//! Crate-private resolver result plumbing.
//!
//! This is a non-serialized scaffold for the proposed resolver boundary.  It
//! deliberately contains no diagnostic registry, resource profile, semantic
//! payload, or public operation API.

#![allow(dead_code)]

use core::fmt;

/// The proposed closed status vocabulary for a semantic resolver operation.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub(crate) enum ResolverStatus {
    /// The operation completed successfully.
    Success,
    /// The authoritative input could not be completely acquired or admitted.
    InputFailure,
    /// Complete supplied source established an invalid source.
    InvalidSource,
    /// A recognized source or capability is unsupported.
    Unsupported,
    /// A required dependency could not be acquired, read, verified, or resolved.
    DependencyFailure,
    /// A configured resource breach prevented required work or trusted completion.
    ResourceLimit,
    /// Internal or environment interruption lost trust in the result.
    InternalFailure,
}

/// The eight proposed resolver phases, in their normative order.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub(crate) enum ResolverPhase {
    /// Raw-byte, UTF-8, and resource admission.
    RawByteUtf8AndResourceAdmission,
    /// Strict JSON parsing and contract recognition.
    StrictJsonParsingAndContractRecognition,
    /// Dependency acquisition, reading, verification, and resolution.
    Dependencies,
    /// Namespace, identity, and reference resolution.
    NamespacesIdentityAndReferences,
    /// Ownership and typed-relation resolution.
    OwnershipAndTypedRelations,
    /// Unit/frame normalization and value derivation.
    UnitFrameNormalizationAndValueDerivation,
    /// Semantic invariant checking.
    SemanticInvariants,
    /// In-memory snapshot finalization and handoff.
    InMemorySnapshotFinalizationAndHandoff,
}

impl ResolverPhase {
    const fn ordinal(self) -> usize {
        match self {
            Self::RawByteUtf8AndResourceAdmission => 0,
            Self::StrictJsonParsingAndContractRecognition => 1,
            Self::Dependencies => 2,
            Self::NamespacesIdentityAndReferences => 3,
            Self::OwnershipAndTypedRelations => 4,
            Self::UnitFrameNormalizationAndValueDerivation => 5,
            Self::SemanticInvariants => 6,
            Self::InMemorySnapshotFinalizationAndHandoff => 7,
        }
    }

    const fn all() -> [Self; 8] {
        [
            Self::RawByteUtf8AndResourceAdmission,
            Self::StrictJsonParsingAndContractRecognition,
            Self::Dependencies,
            Self::NamespacesIdentityAndReferences,
            Self::OwnershipAndTypedRelations,
            Self::UnitFrameNormalizationAndValueDerivation,
            Self::SemanticInvariants,
            Self::InMemorySnapshotFinalizationAndHandoff,
        ]
    }
}

/// A typed observation emitted by one reached phase.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum PhaseOutcome {
    /// The phase completed without establishing a failure status.
    Complete,
    /// Complete acquisition was not available at the admission boundary.
    InputFailure,
    /// Complete source established an invalid-source result.
    InvalidSource,
    /// Complete recognized input established an unsupported result.
    Unsupported,
    /// Required dependency processing was interrupted.
    DependencyFailure,
    /// A configured resource breach prevented required work or a trusted result.
    ResourceLimit,
    /// A non-qualifying resource notice that does not affect status.
    ResourceNotice,
    /// Internal or environment trust was lost.
    InternalTrustLoss,
}

/// One reached phase's status observation and retained diagnostics.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct PhaseObservation<D> {
    phase: ResolverPhase,
    outcome: PhaseOutcome,
    processing_complete: bool,
    diagnostics_complete: bool,
    primary_diagnostic: Option<D>,
    diagnostics: Vec<D>,
}

impl<D> PhaseObservation<D> {
    /// Construct a successful phase observation.
    pub(crate) fn complete(
        phase: ResolverPhase,
        diagnostics_complete: bool,
        diagnostics: Vec<D>,
    ) -> Self {
        Self {
            phase,
            outcome: PhaseOutcome::Complete,
            processing_complete: true,
            diagnostics_complete,
            primary_diagnostic: None,
            diagnostics,
        }
    }

    /// Construct an input-failure observation at the admission phase.
    pub(crate) fn input_failure(
        primary_diagnostic: D,
        diagnostics_complete: bool,
        diagnostics: Vec<D>,
    ) -> Self {
        Self {
            phase: ResolverPhase::RawByteUtf8AndResourceAdmission,
            outcome: PhaseOutcome::InputFailure,
            processing_complete: false,
            diagnostics_complete,
            primary_diagnostic: Some(primary_diagnostic),
            diagnostics,
        }
    }

    /// Construct an invalid-source observation.
    pub(crate) fn invalid_source(
        phase: ResolverPhase,
        primary_diagnostic: D,
        diagnostics_complete: bool,
        diagnostics: Vec<D>,
    ) -> Self {
        Self {
            phase,
            outcome: PhaseOutcome::InvalidSource,
            processing_complete: true,
            diagnostics_complete,
            primary_diagnostic: Some(primary_diagnostic),
            diagnostics,
        }
    }

    /// Construct an unsupported-source observation.
    pub(crate) fn unsupported(
        phase: ResolverPhase,
        primary_diagnostic: D,
        diagnostics_complete: bool,
        diagnostics: Vec<D>,
    ) -> Self {
        Self {
            phase,
            outcome: PhaseOutcome::Unsupported,
            processing_complete: true,
            diagnostics_complete,
            primary_diagnostic: Some(primary_diagnostic),
            diagnostics,
        }
    }

    /// Construct a required dependency interruption observation.
    pub(crate) fn dependency_failure(
        primary_diagnostic: D,
        diagnostics_complete: bool,
        diagnostics: Vec<D>,
    ) -> Self {
        Self {
            phase: ResolverPhase::Dependencies,
            outcome: PhaseOutcome::DependencyFailure,
            processing_complete: false,
            diagnostics_complete,
            primary_diagnostic: Some(primary_diagnostic),
            diagnostics,
        }
    }

    /// Construct a qualifying resource-limit observation.
    pub(crate) fn resource_limit(
        phase: ResolverPhase,
        primary_diagnostic: D,
        diagnostics_complete: bool,
        diagnostics: Vec<D>,
    ) -> Self {
        Self {
            phase,
            outcome: PhaseOutcome::ResourceLimit,
            processing_complete: false,
            diagnostics_complete,
            primary_diagnostic: Some(primary_diagnostic),
            diagnostics,
        }
    }

    /// Construct a non-qualifying resource notice that cannot become
    /// `resource-limit`.
    pub(crate) fn resource_notice(
        phase: ResolverPhase,
        diagnostics_complete: bool,
        diagnostics: Vec<D>,
    ) -> Self {
        Self {
            phase,
            outcome: PhaseOutcome::ResourceNotice,
            processing_complete: true,
            diagnostics_complete,
            primary_diagnostic: None,
            diagnostics,
        }
    }

    /// Construct an internal-trust-loss observation.
    pub(crate) fn internal_trust_loss(
        phase: ResolverPhase,
        primary_diagnostic: D,
        diagnostics_complete: bool,
        diagnostics: Vec<D>,
    ) -> Self {
        Self {
            phase,
            outcome: PhaseOutcome::InternalTrustLoss,
            processing_complete: false,
            diagnostics_complete,
            primary_diagnostic: Some(primary_diagnostic),
            diagnostics,
        }
    }
}

/// Reduced status and retained data before an operation payload is attached.
#[derive(Debug, Eq, PartialEq)]
pub(crate) struct ResolutionReduction<D> {
    status: ResolverStatus,
    processing_complete: bool,
    diagnostics_complete: bool,
    primary_diagnostic: Option<D>,
    diagnostics: Vec<D>,
}

/// A crate-private, non-serialized resolver operation envelope.
#[derive(Debug, Eq, PartialEq)]
pub(crate) struct ResolverEnvelope<T, D> {
    status: ResolverStatus,
    processing_complete: bool,
    diagnostics_complete: bool,
    primary_diagnostic: Option<D>,
    payload: Option<T>,
    diagnostics: Vec<D>,
}

/// A payload/status mismatch while constructing the terminal envelope.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum ResolverEnvelopeConstructionError {
    /// A non-success result cannot carry an operation payload.
    PayloadForFailure,
    /// A successful result that declares a payload requirement must carry one.
    MissingRequiredSuccessPayload,
}

impl<T, D> ResolverEnvelope<T, D> {
    /// Attach an optional operation payload to a reduced result.
    ///
    /// A caller that declares a payload requirement for success receives a
    /// typed construction error when that requirement is violated.  No
    /// payload is fabricated and no new diagnostic vocabulary is introduced.
    pub(crate) fn from_reduction(
        reduction: ResolutionReduction<D>,
        payload: Option<T>,
        success_requires_payload: bool,
    ) -> Result<Self, ResolverEnvelopeConstructionError> {
        let ResolutionReduction {
            status,
            processing_complete,
            diagnostics_complete,
            primary_diagnostic,
            diagnostics,
        } = reduction;

        if status != ResolverStatus::Success && payload.is_some() {
            return Err(ResolverEnvelopeConstructionError::PayloadForFailure);
        }
        if status == ResolverStatus::Success && success_requires_payload && payload.is_none() {
            return Err(ResolverEnvelopeConstructionError::MissingRequiredSuccessPayload);
        }

        Ok(Self {
            status,
            processing_complete,
            diagnostics_complete,
            primary_diagnostic,
            payload,
            diagnostics,
        })
    }

    /// Final status.
    pub(crate) const fn status(&self) -> ResolverStatus {
        self.status
    }

    /// Whether required processing/trusted result work completed.
    pub(crate) const fn processing_complete(&self) -> bool {
        self.processing_complete
    }

    /// Whether all applicable profile-required diagnostics were retained.
    pub(crate) const fn diagnostics_complete(&self) -> bool {
        self.diagnostics_complete
    }

    /// The status-establishing primary diagnostic, when this is a failure.
    pub(crate) fn primary_diagnostic(&self) -> Option<&D> {
        self.primary_diagnostic.as_ref()
    }

    /// Optional operation payload.
    pub(crate) fn payload(&self) -> Option<&T> {
        self.payload.as_ref()
    }

    /// Retained diagnostics in reached-phase order.
    pub(crate) fn diagnostics(&self) -> &[D] {
        &self.diagnostics
    }
}

/// Why a phase observation set cannot establish a deterministic terminal result.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum ResolverReductionError {
    /// No phase observation was supplied.
    NoObservations,
    /// A successful reduction did not observe every ordered phase.
    MissingPhase(ResolverPhase),
    /// A failure was observed without observations for all preceding phases.
    MissingPrecedingPhase(ResolverPhase),
    /// A phase after the fatal phase was observed even though it is blocked.
    ObservationAfterFatal {
        /// The earliest fatal/blocking phase.
        fatal_phase: ResolverPhase,
        /// The later phase that was nevertheless observed.
        observed_phase: ResolverPhase,
    },
    /// Incomplete acquisition was combined with a complete-source outcome in
    /// one phase.
    ContradictorySamePhaseOutcome(ResolverPhase),
    /// A malformed internal observation omitted the selected failure primary.
    MissingPrimaryDiagnostic(ResolverPhase),
}

impl fmt::Display for ResolverReductionError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::NoObservations => formatter.write_str("no resolver phase observations"),
            Self::MissingPhase(phase) => write!(formatter, "missing resolver phase {phase:?}"),
            Self::MissingPrecedingPhase(phase) => {
                write!(formatter, "missing phase preceding {phase:?}")
            }
            Self::ObservationAfterFatal {
                fatal_phase,
                observed_phase,
            } => write!(
                formatter,
                "phase {observed_phase:?} observed after fatal phase {fatal_phase:?}"
            ),
            Self::ContradictorySamePhaseOutcome(phase) => {
                write!(formatter, "contradictory same-phase outcome at {phase:?}")
            }
            Self::MissingPrimaryDiagnostic(phase) => {
                write!(formatter, "missing primary diagnostic at {phase:?}")
            }
        }
    }
}

impl std::error::Error for ResolverReductionError {}

/// Reduce reached phase observations according to the proposed status rules.
///
/// `D: Ord` is intentionally the only diagnostic ordering contract here.  A
/// future diagnostic profile will supply the concrete ordered diagnostic type;
/// this scaffold does not define its fields, codes, or registry semantics.
pub(crate) fn reduce_phase_observations<D: Ord + Clone>(
    mut observations: Vec<PhaseObservation<D>>,
) -> Result<ResolutionReduction<D>, ResolverReductionError> {
    if observations.is_empty() {
        return Err(ResolverReductionError::NoObservations);
    }

    // Stable ordering makes phase order deterministic while preserving the
    // caller's already-determined order among observations in one phase.
    observations.sort_by_key(|observation| observation.phase.ordinal());

    let mut seen = [false; 8];
    for observation in &observations {
        seen[observation.phase.ordinal()] = true;
    }

    // Contradictions are illegal even when another same-phase observation
    // would otherwise have global precedence.
    reject_contradictory_same_phase_outcomes(&observations)?;

    let fatal_phase = observations
        .iter()
        .find(|observation| is_fatal_or_blocking(&observation.outcome))
        .map(|observation| observation.phase);
    if let Some(fatal_phase) = fatal_phase {
        for preceding in ResolverPhase::all()
            .into_iter()
            .filter(|preceding| preceding.ordinal() < fatal_phase.ordinal())
        {
            if !seen[preceding.ordinal()] {
                return Err(ResolverReductionError::MissingPrecedingPhase(fatal_phase));
            }
        }
        if let Some(observation) = observations
            .iter()
            .find(|observation| observation.phase.ordinal() > fatal_phase.ordinal())
        {
            return Err(ResolverReductionError::ObservationAfterFatal {
                fatal_phase,
                observed_phase: observation.phase,
            });
        }
    }

    let internal_phase = observations
        .iter()
        .filter(|observation| matches!(observation.outcome, PhaseOutcome::InternalTrustLoss))
        .map(|observation| observation.phase);
    let resource_phase = observations.iter().filter_map(|observation| {
        matches!(observation.outcome, PhaseOutcome::ResourceLimit).then_some(observation.phase)
    });

    let ordinary_failure = select_ordinary_failure(&observations)?;
    let selected = internal_phase
        .min_by_key(|phase| phase.ordinal())
        .map(|phase| (phase, ResolverStatus::InternalFailure))
        .or_else(|| {
            resource_phase
                .min_by_key(|phase| phase.ordinal())
                .map(|phase| (phase, ResolverStatus::ResourceLimit))
        })
        .or(ordinary_failure);

    let (status, cutoff) = match selected {
        Some((phase, status)) => (status, phase),
        None => {
            for phase in ResolverPhase::all() {
                if !seen[phase.ordinal()] {
                    return Err(ResolverReductionError::MissingPhase(phase));
                }
            }
            (
                ResolverStatus::Success,
                ResolverPhase::InMemorySnapshotFinalizationAndHandoff,
            )
        }
    };

    let cutoff_ordinal = cutoff.ordinal();
    let reached = observations
        .iter()
        .filter(|observation| observation.phase.ordinal() <= cutoff_ordinal);
    let diagnostics_complete = reached
        .clone()
        .all(|observation| observation.diagnostics_complete);
    let processing_complete = match status {
        ResolverStatus::Success => reached
            .clone()
            .all(|observation| observation.processing_complete),
        ResolverStatus::InvalidSource | ResolverStatus::Unsupported => true,
        ResolverStatus::InputFailure
        | ResolverStatus::DependencyFailure
        | ResolverStatus::ResourceLimit
        | ResolverStatus::InternalFailure => false,
    };
    let mut primary_candidates = Vec::new();
    let mut diagnostic_groups = Vec::new();
    let mut phase_diagnostics = Vec::new();
    let mut current_phase = None;
    for observation in observations
        .into_iter()
        .filter(|observation| observation.phase.ordinal() <= cutoff_ordinal)
    {
        if current_phase != Some(observation.phase) {
            if current_phase.is_some() {
                diagnostic_groups.push(core::mem::take(&mut phase_diagnostics));
            }
            current_phase = Some(observation.phase);
        }
        let establishes_selected_status = establishes_status(&observation.outcome, status);
        let mut observation_diagnostics = observation.diagnostics;
        if let Some(primary) = observation.primary_diagnostic {
            if establishes_selected_status {
                primary_candidates.push(primary.clone());
            }
            observation_diagnostics.push(primary);
        }
        phase_diagnostics.extend(observation_diagnostics);
    }
    diagnostic_groups.push(phase_diagnostics);
    let mut diagnostics = Vec::new();
    for mut group in diagnostic_groups {
        group.sort();
        diagnostics.extend(group);
    }

    let primary_diagnostic = if status == ResolverStatus::Success {
        None
    } else {
        Some(
            primary_candidates
                .into_iter()
                .min()
                .ok_or(ResolverReductionError::MissingPrimaryDiagnostic(cutoff))?,
        )
    };

    Ok(ResolutionReduction {
        status,
        processing_complete,
        diagnostics_complete,
        primary_diagnostic,
        diagnostics,
    })
}

fn is_fatal_or_blocking(outcome: &PhaseOutcome) -> bool {
    matches!(
        outcome,
        PhaseOutcome::InputFailure
            | PhaseOutcome::InvalidSource
            | PhaseOutcome::Unsupported
            | PhaseOutcome::DependencyFailure
            | PhaseOutcome::ResourceLimit
            | PhaseOutcome::InternalTrustLoss
    )
}

fn establishes_status(outcome: &PhaseOutcome, status: ResolverStatus) -> bool {
    matches!(
        (outcome, status),
        (PhaseOutcome::InputFailure, ResolverStatus::InputFailure)
            | (PhaseOutcome::InvalidSource, ResolverStatus::InvalidSource)
            | (PhaseOutcome::Unsupported, ResolverStatus::Unsupported)
            | (
                PhaseOutcome::DependencyFailure,
                ResolverStatus::DependencyFailure
            )
            | (PhaseOutcome::ResourceLimit, ResolverStatus::ResourceLimit)
            | (
                PhaseOutcome::InternalTrustLoss,
                ResolverStatus::InternalFailure
            )
    )
}

fn reject_contradictory_same_phase_outcomes<D>(
    observations: &[PhaseObservation<D>],
) -> Result<(), ResolverReductionError> {
    let mut index = 0;
    while index < observations.len() {
        let phase = observations[index].phase;
        let end = observations[index..]
            .iter()
            .position(|observation| observation.phase != phase)
            .map_or(observations.len(), |offset| index + offset);
        let group = &observations[index..end];
        let has_input = group
            .iter()
            .any(|observation| matches!(observation.outcome, PhaseOutcome::InputFailure));
        let has_complete_source_outcome = group.iter().any(|observation| {
            matches!(
                observation.outcome,
                PhaseOutcome::InvalidSource | PhaseOutcome::Unsupported
            )
        });
        if has_input && has_complete_source_outcome {
            return Err(ResolverReductionError::ContradictorySamePhaseOutcome(phase));
        }
        index = end;
    }
    Ok(())
}

fn select_ordinary_failure<D>(
    observations: &[PhaseObservation<D>],
) -> Result<Option<(ResolverPhase, ResolverStatus)>, ResolverReductionError> {
    let mut index = 0;
    while index < observations.len() {
        let phase = observations[index].phase;
        let end = observations[index..]
            .iter()
            .position(|observation| observation.phase != phase)
            .map_or(observations.len(), |offset| index + offset);
        let group = &observations[index..end];

        let mut saw_input = false;
        let mut saw_dependency = false;
        let mut saw_invalid = false;
        let mut saw_unsupported = false;
        for observation in group {
            match observation.outcome {
                PhaseOutcome::InputFailure => saw_input = true,
                PhaseOutcome::DependencyFailure => saw_dependency = true,
                PhaseOutcome::InvalidSource => saw_invalid = true,
                PhaseOutcome::Unsupported => saw_unsupported = true,
                PhaseOutcome::Complete
                | PhaseOutcome::ResourceLimit
                | PhaseOutcome::ResourceNotice
                | PhaseOutcome::InternalTrustLoss => {}
            }
        }

        let selected = if phase == ResolverPhase::Dependencies && saw_dependency {
            Some(ResolverStatus::DependencyFailure)
        } else if saw_invalid {
            Some(ResolverStatus::InvalidSource)
        } else if saw_unsupported {
            Some(ResolverStatus::Unsupported)
        } else if saw_input {
            Some(ResolverStatus::InputFailure)
        } else {
            None
        };

        if let Some(status) = selected {
            return Ok(Some((phase, status)));
        }
        index = end;
    }
    Ok(None)
}

#[cfg(test)]
mod tests {
    use super::*;

    type Observation = PhaseObservation<&'static str>;

    fn all_success() -> Vec<Observation> {
        ResolverPhase::all()
            .into_iter()
            .map(|phase| Observation::complete(phase, true, Vec::new()))
            .collect()
    }

    fn prefix_before(phase: ResolverPhase) -> Vec<Observation> {
        ResolverPhase::all()
            .into_iter()
            .filter(|candidate| candidate.ordinal() < phase.ordinal())
            .map(|candidate| Observation::complete(candidate, true, Vec::new()))
            .collect()
    }

    #[test]
    fn phase_order_and_success_coverage_are_closed() {
        let mut observations = all_success();
        observations.reverse();
        let reduction = reduce_phase_observations(observations).unwrap();
        assert_eq!(reduction.status, ResolverStatus::Success);
        assert!(reduction.processing_complete);
        assert!(reduction.diagnostics_complete);

        let missing = reduce_phase_observations(all_success()[..7].to_vec()).unwrap_err();
        assert_eq!(
            missing,
            ResolverReductionError::MissingPhase(
                ResolverPhase::InMemorySnapshotFinalizationAndHandoff
            )
        );

        let input_failure = Observation::input_failure("input", true, vec!["extra"]);
        assert_eq!(
            input_failure.phase,
            ResolverPhase::RawByteUtf8AndResourceAdmission
        );
        let input_failure = reduce_phase_observations(vec![input_failure]).unwrap();
        assert_eq!(input_failure.status, ResolverStatus::InputFailure);
        assert!(!input_failure.processing_complete);
        assert!(input_failure.diagnostics_complete);
        assert_eq!(input_failure.primary_diagnostic, Some("input"));
        assert_eq!(input_failure.diagnostics, vec!["extra", "input"]);
    }

    #[test]
    fn internal_trust_loss_precedes_resource_and_source_failure_in_reached_phase() {
        let phase = ResolverPhase::SemanticInvariants;
        let mut observations = prefix_before(phase);
        observations.extend([
            Observation::invalid_source(phase, "invalid", true, vec!["invalid-detail"]),
            Observation::resource_limit(phase, "resource", true, vec!["resource-detail"]),
            Observation::internal_trust_loss(phase, "internal", true, vec!["internal-detail"]),
        ]);
        let reduction = reduce_phase_observations(observations).unwrap();
        assert_eq!(reduction.status, ResolverStatus::InternalFailure);
        assert!(!reduction.processing_complete);
        assert!(reduction.diagnostics_complete);
        assert_eq!(reduction.primary_diagnostic, Some("internal"));
        assert_eq!(
            reduction.diagnostics,
            vec![
                "internal",
                "internal-detail",
                "invalid",
                "invalid-detail",
                "resource",
                "resource-detail"
            ]
        );
    }

    #[test]
    fn global_interruptions_require_predecessors_and_later_phases_are_blocked() {
        let phase = ResolverPhase::SemanticInvariants;
        let missing_internal = reduce_phase_observations(vec![Observation::internal_trust_loss(
            phase,
            "internal",
            true,
            Vec::new(),
        )])
        .unwrap_err();
        assert_eq!(
            missing_internal,
            ResolverReductionError::MissingPrecedingPhase(phase)
        );

        let missing_resource = reduce_phase_observations(vec![Observation::resource_limit(
            phase,
            "resource",
            true,
            Vec::new(),
        )])
        .unwrap_err();
        assert_eq!(
            missing_resource,
            ResolverReductionError::MissingPrecedingPhase(phase)
        );

        let mut post_fatal = prefix_before(phase);
        post_fatal.push(Observation::invalid_source(
            phase,
            "invalid",
            true,
            Vec::new(),
        ));
        post_fatal.push(Observation::complete(
            ResolverPhase::InMemorySnapshotFinalizationAndHandoff,
            true,
            Vec::new(),
        ));
        assert_eq!(
            reduce_phase_observations(post_fatal).unwrap_err(),
            ResolverReductionError::ObservationAfterFatal {
                fatal_phase: phase,
                observed_phase: ResolverPhase::InMemorySnapshotFinalizationAndHandoff,
            }
        );
    }

    #[test]
    fn qualifying_resource_and_nonqualifying_notice_have_distinct_status_effects() {
        let phase = ResolverPhase::SemanticInvariants;
        let mut observations = prefix_before(phase);
        observations.extend([
            Observation::unsupported(phase, "unsupported", true, Vec::new()),
            Observation::resource_limit(phase, "resource", true, Vec::new()),
        ]);
        assert_eq!(
            reduce_phase_observations(observations).unwrap().status,
            ResolverStatus::ResourceLimit
        );

        let mut observations = prefix_before(phase);
        observations.extend([
            Observation::unsupported(phase, "unsupported", true, Vec::new()),
            Observation::resource_notice(phase, true, vec!["notice"]),
        ]);
        let reduction = reduce_phase_observations(observations).unwrap();
        assert_eq!(reduction.status, ResolverStatus::Unsupported);
        assert_eq!(reduction.primary_diagnostic, Some("unsupported"));
    }

    #[test]
    fn dependency_same_phase_precedence_is_dependency_invalid_then_unsupported() {
        let phase = ResolverPhase::Dependencies;
        let mut observations = prefix_before(phase);
        observations.extend([
            Observation::unsupported(phase, "unsupported", true, vec!["u"]),
            Observation::invalid_source(phase, "invalid", true, vec!["i"]),
            Observation::dependency_failure("dependency", true, vec!["d"]),
        ]);
        let reduction = reduce_phase_observations(observations).unwrap();
        assert_eq!(reduction.status, ResolverStatus::DependencyFailure);
        assert_eq!(reduction.primary_diagnostic, Some("dependency"));

        let mut observations = prefix_before(phase);
        observations.extend([
            Observation::unsupported(phase, "unsupported", true, Vec::new()),
            Observation::invalid_source(phase, "invalid", true, Vec::new()),
        ]);
        let reduction = reduce_phase_observations(observations).unwrap();
        assert_eq!(reduction.status, ResolverStatus::InvalidSource);
        assert_eq!(reduction.primary_diagnostic, Some("invalid"));

        let mut observations = prefix_before(phase);
        observations.push(Observation::unsupported(
            phase,
            "unsupported",
            true,
            Vec::new(),
        ));
        assert_eq!(
            reduce_phase_observations(observations).unwrap().status,
            ResolverStatus::Unsupported
        );
    }

    #[test]
    fn processing_and_diagnostic_completeness_are_independent() {
        let phase = ResolverPhase::StrictJsonParsingAndContractRecognition;
        assert!(
            Observation::invalid_source(phase, "invalid", true, Vec::new()).processing_complete
        );
        assert!(
            Observation::unsupported(phase, "unsupported", true, Vec::new()).processing_complete
        );
        let mut observations = prefix_before(phase);
        observations.push(Observation::complete(
            ResolverPhase::RawByteUtf8AndResourceAdmission,
            false,
            vec!["retained"],
        ));
        observations.push(Observation::invalid_source(
            phase,
            "invalid",
            true,
            Vec::new(),
        ));
        let reduction = reduce_phase_observations(observations).unwrap();
        assert_eq!(reduction.status, ResolverStatus::InvalidSource);
        assert!(reduction.processing_complete);
        assert!(!reduction.diagnostics_complete);
    }

    #[test]
    fn payload_legality_is_typed_and_success_payload_policy_is_explicit() {
        let missing = ResolverEnvelope::<u8, &str>::from_reduction(
            reduce_phase_observations(all_success()).unwrap(),
            None,
            true,
        )
        .unwrap_err();
        assert_eq!(
            missing,
            ResolverEnvelopeConstructionError::MissingRequiredSuccessPayload
        );

        let success = ResolverEnvelope::<u8, &str>::from_reduction(
            reduce_phase_observations(all_success()).unwrap(),
            None,
            false,
        )
        .unwrap();
        assert_eq!(success.status(), ResolverStatus::Success);
        assert!(success.processing_complete());
        assert!(success.primary_diagnostic().is_none());

        let failure = ResolverEnvelope::<u8, &str>::from_reduction(
            reduce_phase_observations(vec![Observation::input_failure(
                "input",
                false,
                vec!["input"],
            )])
            .unwrap(),
            Some(1),
            false,
        )
        .unwrap_err();
        assert_eq!(
            failure,
            ResolverEnvelopeConstructionError::PayloadForFailure
        );
    }

    #[test]
    fn primary_and_diagnostic_order_is_permutation_invariant_within_phase() {
        let phase = ResolverPhase::StrictJsonParsingAndContractRecognition;
        let mut first = prefix_before(phase);
        first.extend([
            Observation::invalid_source(phase, "z", true, vec!["m"]),
            Observation::invalid_source(phase, "a", true, vec!["n"]),
        ]);
        let mut second = prefix_before(phase);
        second.extend([
            Observation::invalid_source(phase, "a", true, vec!["n"]),
            Observation::invalid_source(phase, "z", true, vec!["m"]),
        ]);
        let first = reduce_phase_observations(first).unwrap();
        let second = reduce_phase_observations(second).unwrap();
        assert_eq!(first.primary_diagnostic, Some("a"));
        assert_eq!(first, second);
        assert_eq!(first.diagnostics, vec!["a", "m", "n", "z"]);
    }

    #[test]
    fn contradictory_input_and_complete_source_observations_are_rejected() {
        let error = reduce_phase_observations(vec![
            Observation::input_failure("input", true, Vec::new()),
            Observation::invalid_source(
                ResolverPhase::RawByteUtf8AndResourceAdmission,
                "invalid",
                true,
                Vec::new(),
            ),
        ])
        .unwrap_err();
        assert_eq!(
            error,
            ResolverReductionError::ContradictorySamePhaseOutcome(
                ResolverPhase::RawByteUtf8AndResourceAdmission
            )
        );
    }
}
