//! Research-only same-process floating-point attestation and square-root
//! provider for EXP-0002.
//!
//! This module deliberately does not select a numeric profile, change the
//! floating-point environment, or provide expected corpus values.  The
//! supported implementation is restricted to the x86_64 GNU/Linux target
//! used for this experiment.  Other targets compile to an explicit
//! fail-closed backend.
//!
//! The adapter must be single-threaded while a provider is in use.  The
//! supported backend reads the current C/x87 rounding mode and MXCSR before
//! and after each host `f64::sqrt` call.  It never calls `fesetround`, writes
//! MXCSR, runs arithmetic probes, or otherwise repairs the process
//! environment.  The small unsafe boundary is isolated to the target-specific
//! reads below; the core crate remains free of unsafe code.
//!
//! `observe_environment` is therefore read-only and does not set sticky
//! exception-status flags.  The provider's `f64::sqrt` may naturally alter
//! exception status; its raw pre/post MXCSR observations retain that evidence
//! without claiming that the adapter controls or restores it.

use creature_kernel_core::quaternion_normalization::{CorrectlyRoundedSqrt, SqrtProviderFailure};

/// The environment state observed at one point in the candidate process.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct EnvironmentObservation {
    /// Compile-time target classification used by this adapter.
    pub target: &'static str,
    /// Whether all required observations passed.
    pub status: EnvironmentStatus,
    /// The C floating-point rounding mode, when it was readable.
    pub rounding_mode: Option<i32>,
    /// The x86 MXCSR register, when it was readable.
    pub mxcsr: Option<u32>,
    /// MXCSR rounding-control code from bits 13-14, when readable.
    ///
    /// `0` is round-to-nearest (the required value); `1`, `2`, and `3` are
    /// the other MXCSR rounding modes.  This is retained separately from
    /// the C/x87 `fegetround` result.
    pub mxcsr_rounding_mode: Option<u8>,
    /// The first failed requirement, if any.
    pub failure: Option<EnvironmentFailure>,
}

impl EnvironmentObservation {
    #[allow(dead_code)]
    const fn unsupported(target: &'static str) -> Self {
        Self {
            target,
            status: EnvironmentStatus::Unsupported,
            rounding_mode: None,
            mxcsr: None,
            mxcsr_rounding_mode: None,
            failure: Some(EnvironmentFailure::UnsupportedTarget),
        }
    }

    /// Return whether this observation is sufficient to construct the host
    /// square-root capability.
    pub const fn is_passed(self) -> bool {
        matches!(self.status, EnvironmentStatus::Passed)
    }
}

/// Result of attempting the environment observations.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum EnvironmentStatus {
    /// All required same-process observations passed.
    Passed,
    /// The target has no implementation of the required reads.
    Unsupported,
    /// A supported environment check was readable but failed its requirement.
    Failed,
}

/// Why the environment could not be admitted as a provider capability.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum EnvironmentFailure {
    /// The compile-time target is outside this bounded adapter.
    UnsupportedTarget,
    /// The C runtime did not expose a determinable x87 rounding mode.
    RoundingModeUnavailable { observed: i32 },
    /// The x87/C mode or MXCSR rounding-control code was not round-to-nearest.
    /// For an MXCSR failure, `observed` is the decoded 0..=3 control code.
    WrongRoundingMode { observed: i32 },
    /// MXCSR flush-to-zero was enabled.
    FtzEnabled { mxcsr: u32 },
    /// MXCSR denormals-are-zero was enabled.
    DazEnabled { mxcsr: u32 },
}

/// The outcome retained for one provider invocation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum SqrtTraceOutcome {
    /// The environment passed both checks and the output was finite.
    Succeeded,
    /// The provider failed closed.
    Failed,
}

/// A failure retained in a square-root trace entry.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum SqrtTraceFailure {
    /// The pre- or post-call environment observation failed.
    Environment(EnvironmentFailure),
    /// The provider was asked to evaluate a negative or NaN input.
    InvalidInput,
    /// The host operation returned a non-finite value.
    NonFiniteOutput,
}

/// Evidence for one attempted provider call.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct SqrtTraceEntry {
    /// One-based provider invocation number.
    pub call_index: u64,
    /// Raw binary64 input bits supplied to `f64::sqrt` if it was called.
    pub input_bits: u64,
    /// Raw binary64 output bits, when the host operation returned.
    pub output_bits: Option<u64>,
    /// Environment state immediately before the host operation or rejection.
    pub pre: EnvironmentObservation,
    /// Environment state immediately after the host operation, when called.
    pub post: Option<EnvironmentObservation>,
    /// Whether the provider returned a value or failed closed.
    pub outcome: SqrtTraceOutcome,
    /// Failure detail, when the outcome failed.
    pub failure: Option<SqrtTraceFailure>,
}

/// Read the current environment without changing it.
pub fn observe_environment() -> EnvironmentObservation {
    platform::observe_environment()
}

/// Read and validate the current environment without changing it.
pub fn attest_environment() -> Result<EnvironmentObservation, EnvironmentFailure> {
    let observation = observe_environment();
    match observation.failure {
        None if observation.is_passed() => Ok(observation),
        Some(failure) => Err(failure),
        None => Err(EnvironmentFailure::UnsupportedTarget),
    }
}

/// A dynamic host square-root provider guarded by same-process observations.
pub struct AttestedHostSqrt {
    initial: EnvironmentObservation,
    trace: Vec<SqrtTraceEntry>,
}

impl AttestedHostSqrt {
    /// Construct the provider only after the initial environment attestation.
    pub fn new() -> Result<Self, EnvironmentFailure> {
        let initial = attest_environment()?;
        Ok(Self {
            initial,
            trace: Vec::new(),
        })
    }

    /// Return the initial environment observation used to admit this provider.
    pub const fn initial_observation(&self) -> EnvironmentObservation {
        self.initial
    }

    /// Return all provider call evidence in invocation order.
    pub fn trace(&self) -> &[SqrtTraceEntry] {
        &self.trace
    }

    /// Return the number of provider invocations, including failed attempts.
    pub const fn call_count(&self) -> u64 {
        self.trace.len() as u64
    }

    fn push_failure(
        &mut self,
        call_index: u64,
        input_bits: u64,
        pre: EnvironmentObservation,
        post: Option<EnvironmentObservation>,
        output_bits: Option<u64>,
        failure: SqrtTraceFailure,
    ) -> Result<f64, SqrtProviderFailure> {
        self.trace.push(SqrtTraceEntry {
            call_index,
            input_bits,
            output_bits,
            pre,
            post,
            outcome: SqrtTraceOutcome::Failed,
            failure: Some(failure),
        });
        Err(SqrtProviderFailure::Failed)
    }
}

impl CorrectlyRoundedSqrt for AttestedHostSqrt {
    fn sqrt(&mut self, input: f64) -> Result<f64, SqrtProviderFailure> {
        let call_index = self.call_count() + 1;
        let input_bits = input.to_bits();
        let pre = observe_environment();
        if let Some(failure) = pre.failure {
            return self.push_failure(
                call_index,
                input_bits,
                pre,
                None,
                None,
                SqrtTraceFailure::Environment(failure),
            );
        }
        if !input.is_finite() || input.is_sign_negative() && input != 0.0 {
            return self.push_failure(
                call_index,
                input_bits,
                pre,
                None,
                None,
                SqrtTraceFailure::InvalidInput,
            );
        }

        let output = input.sqrt();
        let output_bits = output.to_bits();
        let post = observe_environment();
        if let Some(failure) = post.failure {
            return self.push_failure(
                call_index,
                input_bits,
                pre,
                Some(post),
                Some(output_bits),
                SqrtTraceFailure::Environment(failure),
            );
        }
        if !output.is_finite() {
            return self.push_failure(
                call_index,
                input_bits,
                pre,
                Some(post),
                Some(output_bits),
                SqrtTraceFailure::NonFiniteOutput,
            );
        }

        self.trace.push(SqrtTraceEntry {
            call_index,
            input_bits,
            output_bits: Some(output_bits),
            pre,
            post: Some(post),
            outcome: SqrtTraceOutcome::Succeeded,
            failure: None,
        });
        Ok(output)
    }
}

#[cfg(all(target_arch = "x86_64", target_os = "linux", target_env = "gnu"))]
mod platform {
    use super::{EnvironmentFailure, EnvironmentObservation, EnvironmentStatus};
    use core::ffi::c_int;

    const TARGET: &str = "x86_64-unknown-linux-gnu";
    const FE_TONEAREST: c_int = 0;
    const MXCSR_FTZ: u32 = 1 << 15;
    const MXCSR_DAZ: u32 = 1 << 6;
    const MXCSR_ROUNDING_MASK: u32 = 0b11 << 13;
    const MXCSR_ROUNDING_SHIFT: u32 = 13;
    const MXCSR_ROUNDING_NEAREST: u8 = 0;

    unsafe extern "C" {
        fn fegetround() -> c_int;
    }

    /// Read MXCSR without modifying it.
    fn read_mxcsr() -> u32 {
        let mut value = 0_u32;
        // SAFETY: this module is compiled only for x86_64. `stmxcsr` stores
        // the current thread's MXCSR to the valid stack location supplied by
        // the compiler. It does not modify MXCSR or the floating-point state.
        unsafe {
            std::arch::asm!(
                "stmxcsr [{ptr}]",
                ptr = in(reg) &mut value,
                options(nostack, preserves_flags),
            );
        }
        value
    }

    /// Decode MXCSR bits 13-14 without touching the floating-point state.
    const fn decode_mxcsr_rounding(mxcsr: u32) -> u8 {
        ((mxcsr & MXCSR_ROUNDING_MASK) >> MXCSR_ROUNDING_SHIFT) as u8
    }

    pub fn observe_environment() -> EnvironmentObservation {
        // SAFETY: fegetround is a read-only C99 floating-point environment
        // query, and the x86_64 GNU/Linux backend supplies the symbol.
        let rounding_mode = unsafe { fegetround() };
        let mxcsr = read_mxcsr();
        let mxcsr_rounding = decode_mxcsr_rounding(mxcsr);

        let failure = if rounding_mode < 0 {
            Some(EnvironmentFailure::RoundingModeUnavailable {
                observed: rounding_mode,
            })
        } else if rounding_mode != FE_TONEAREST {
            Some(EnvironmentFailure::WrongRoundingMode {
                observed: rounding_mode,
            })
        } else if mxcsr_rounding != MXCSR_ROUNDING_NEAREST {
            Some(EnvironmentFailure::WrongRoundingMode {
                observed: mxcsr_rounding as i32,
            })
        } else if mxcsr & MXCSR_FTZ != 0 {
            Some(EnvironmentFailure::FtzEnabled { mxcsr })
        } else if mxcsr & MXCSR_DAZ != 0 {
            Some(EnvironmentFailure::DazEnabled { mxcsr })
        } else {
            None
        };

        EnvironmentObservation {
            target: TARGET,
            status: if failure.is_none() {
                EnvironmentStatus::Passed
            } else {
                EnvironmentStatus::Failed
            },
            rounding_mode: Some(rounding_mode),
            mxcsr: Some(mxcsr),
            mxcsr_rounding_mode: Some(mxcsr_rounding),
            failure,
        }
    }

    #[cfg(test)]
    mod tests {
        use super::{MXCSR_ROUNDING_SHIFT, decode_mxcsr_rounding};

        #[test]
        fn mxcsr_rounding_bits_decode_all_modes() {
            assert_eq!(decode_mxcsr_rounding(0), 0);
            assert_eq!(decode_mxcsr_rounding(1 << MXCSR_ROUNDING_SHIFT), 1);
            assert_eq!(decode_mxcsr_rounding(2 << MXCSR_ROUNDING_SHIFT), 2);
            assert_eq!(decode_mxcsr_rounding(3 << MXCSR_ROUNDING_SHIFT), 3);
        }

        #[test]
        fn mxcsr_rounding_decode_ignores_other_bits() {
            let mxcsr = (3 << MXCSR_ROUNDING_SHIFT) | (1 << 15) | (1 << 6) | 0x3f;
            assert_eq!(decode_mxcsr_rounding(mxcsr), 3);
        }
    }
}

#[cfg(not(all(target_arch = "x86_64", target_os = "linux", target_env = "gnu")))]
mod platform {
    use super::{EnvironmentObservation, EnvironmentStatus};

    pub fn observe_environment() -> EnvironmentObservation {
        EnvironmentObservation::unsupported("unsupported-target")
    }

    #[allow(dead_code)]
    const _: EnvironmentStatus = EnvironmentStatus::Unsupported;
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn observation_never_changes_the_reported_environment() {
        let before = observe_environment();
        let after = observe_environment();
        if before.status == EnvironmentStatus::Passed {
            // Observation consists only of read-only queries, so even the
            // raw MXCSR evidence must be stable across consecutive calls.
            assert_eq!(before, after);
            assert_eq!(before.mxcsr_rounding_mode, Some(0));
        } else {
            assert!(matches!(
                before.status,
                EnvironmentStatus::Failed | EnvironmentStatus::Unsupported
            ));
            assert!(before.failure.is_some());
        }
    }

    #[test]
    fn host_provider_records_a_single_dynamic_call() {
        let Ok(mut provider) = AttestedHostSqrt::new() else {
            return;
        };
        let result = provider.sqrt(2.0).unwrap();
        assert_eq!(result.to_bits(), 0x3ff6_a09e_667f_3bcd);
        assert_eq!(provider.call_count(), 1);
        let entry = provider.trace()[0];
        assert_eq!(entry.call_index, 1);
        assert_eq!(entry.input_bits, 0x4000_0000_0000_0000);
        assert_eq!(entry.output_bits, Some(0x3ff6_a09e_667f_3bcd));
        assert_eq!(entry.outcome, SqrtTraceOutcome::Succeeded);
        assert_eq!(entry.failure, None);
        assert!(entry.pre.is_passed());
        assert!(entry.post.is_some_and(EnvironmentObservation::is_passed));
    }

    #[test]
    fn invalid_input_fails_without_calling_host_sqrt() {
        let Ok(mut provider) = AttestedHostSqrt::new() else {
            return;
        };
        assert_eq!(
            provider.sqrt(f64::NEG_INFINITY),
            Err(SqrtProviderFailure::Failed)
        );
        assert_eq!(provider.call_count(), 1);
        let entry = provider.trace()[0];
        assert_eq!(entry.output_bits, None);
        assert_eq!(entry.post, None);
        assert_eq!(entry.failure, Some(SqrtTraceFailure::InvalidInput));
    }
}
