//! Crate-private coordination of canonical placement for an admitted source set.
//!
//! This is the narrow bridge between the independent canonical frame/value
//! preparation projection and the independent single-member placement
//! projection.  It validates the source-set boundary, visits members in
//! [`SourceSetMemberKey`] order, and keeps upstream frame preparation separate
//! from placement.  It does not merge namespaces, resolve cross-member
//! references, select Attachment candidates, produce aggregate status, or
//! activate a snapshot/runtime contract.

#![allow(dead_code)]
#![allow(clippy::result_large_err)]

use crate::canonical_member_frame_values::{
    CanonicalMemberFrameValues, CanonicalMemberFrameValuesError,
};
use crate::canonical_member_placement::{
    CanonicalMemberPlacement, CanonicalMemberPlacementError, prepare_canonical_member_placement,
};
use crate::quaternion_normalization::{
    Binary64ArithmeticCapability, Binary64ArithmeticProvider, CorrectlyRoundedSqrt,
    QuaternionNormalizationGate, SqrtCapability,
};
use crate::restricted_source_set_handoff::RestrictedSourceSetHandoff;
use crate::source_set_canonical_values::CanonicalSourceSetFrameValues;
use crate::source_set_preparation::{SourceSetMemberKey, SourceSetMemberRole};
use std::collections::{BTreeMap, BTreeSet};
use std::fmt;

/// A source-set boundary mismatch prevents pairing the wrong source member
/// with canonical values.  Upstream per-member failures are not represented
/// here: they are retained in [`CanonicalSourceSetMemberPlacementResult`].
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum CanonicalSourceSetPlacementError {
    /// The designated root differs between the handoff and canonical values.
    RootMismatch {
        /// Root retained by the source-set handoff.
        handoff_root: SourceSetMemberKey,
        /// Root retained by the canonical frame values.
        values_root: SourceSetMemberKey,
    },
    /// A handoff member has no corresponding canonical frame-value entry.
    MissingCanonicalMember {
        /// Member that could not be paired.
        member: SourceSetMemberKey,
    },
    /// Canonical frame values contain an entry not admitted by the handoff.
    UnexpectedCanonicalMember {
        /// Unadmitted canonical member.
        member: SourceSetMemberKey,
    },
    /// The retained root/dependency role differs at one member key.
    MemberRoleMismatch {
        /// Member whose role does not match.
        member: SourceSetMemberKey,
        /// Role admitted by the handoff.
        handoff_role: SourceSetMemberRole,
        /// Role retained by canonical values.
        values_role: SourceSetMemberRole,
    },
    /// A successful canonical value object disagrees with its map key or role.
    CanonicalValueIdentityMismatch {
        /// Map key at which the mismatch was observed.
        member: SourceSetMemberKey,
        /// Identity retained inside the canonical value object.
        values_member: SourceSetMemberKey,
        /// Role admitted by the handoff.
        expected_role: SourceSetMemberRole,
        /// Role retained inside the canonical value object.
        values_role: SourceSetMemberRole,
    },
}

impl fmt::Display for CanonicalSourceSetPlacementError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::RootMismatch {
                handoff_root,
                values_root,
            } => write!(
                formatter,
                "canonical placement root mismatch: handoff {handoff_root:?}, values {values_root:?}"
            ),
            Self::MissingCanonicalMember { member } => write!(
                formatter,
                "canonical placement member is missing frame values: {member:?}"
            ),
            Self::UnexpectedCanonicalMember { member } => write!(
                formatter,
                "canonical placement contains an unadmitted member: {member:?}"
            ),
            Self::MemberRoleMismatch {
                member,
                handoff_role,
                values_role,
            } => write!(
                formatter,
                "canonical placement role mismatch at {member:?}: handoff {handoff_role:?}, values {values_role:?}"
            ),
            Self::CanonicalValueIdentityMismatch {
                member,
                values_member,
                expected_role,
                values_role,
            } => write!(
                formatter,
                "canonical value identity mismatch at {member:?}: value {values_member:?}/{values_role:?}, expected role {expected_role:?}"
            ),
        }
    }
}

impl std::error::Error for CanonicalSourceSetPlacementError {}

/// Independent per-member canonical-frame and placement outcomes.
///
/// `canonical_frame_values` is always present as either success or the exact
/// upstream failure.  `placement` is `None` only when upstream canonical frame
/// preparation failed, making that skip distinct from a placement failure
/// (`Some(Err(_))`) and placement success (`Some(Ok(_))`).
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct CanonicalSourceSetMemberPlacementResult {
    role: SourceSetMemberRole,
    canonical_frame_values: Result<CanonicalMemberFrameValues, CanonicalMemberFrameValuesError>,
    placement: Option<Result<CanonicalMemberPlacement, CanonicalMemberPlacementError>>,
}

impl CanonicalSourceSetMemberPlacementResult {
    /// Root/dependency role retained from the admitted handoff.
    #[must_use]
    pub(crate) const fn role(&self) -> SourceSetMemberRole {
        self.role
    }

    /// Exact upstream canonical frame/value result.
    pub(crate) fn canonical_frame_values(
        &self,
    ) -> &Result<CanonicalMemberFrameValues, CanonicalMemberFrameValuesError> {
        &self.canonical_frame_values
    }

    /// Placement result, or `None` when upstream canonicalization failed.
    #[must_use]
    pub(crate) fn placement(
        &self,
    ) -> Option<&Result<CanonicalMemberPlacement, CanonicalMemberPlacementError>> {
        self.placement.as_ref()
    }
}

/// Deterministic source-set canonical placement results.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct CanonicalSourceSetPlacement {
    root: SourceSetMemberKey,
    members: BTreeMap<SourceSetMemberKey, CanonicalSourceSetMemberPlacementResult>,
}

impl CanonicalSourceSetPlacement {
    /// Designated source-set root retained unchanged.
    #[must_use]
    pub(crate) fn root(&self) -> &SourceSetMemberKey {
        &self.root
    }

    /// Every admitted member in deterministic key order.
    #[must_use]
    pub(crate) fn members(
        &self,
    ) -> &BTreeMap<SourceSetMemberKey, CanonicalSourceSetMemberPlacementResult> {
        &self.members
    }
}

/// Coordinate canonical placement for every admitted source-set member.
///
/// The handoff and canonical frame-value maps must describe the same root,
/// member keys, and roles.  Once that boundary is validated, each successful
/// upstream member receives fresh gate/arithmetic/square-root capabilities
/// from the supplied factories.  Factory calls occur in member-key order as
/// gate, arithmetic, then square root.  A failed upstream member retains its
/// failure and skips all three placement factories; a placement failure is
/// retained only for that member and does not stop later members.
pub(crate) fn prepare_canonical_source_set_placement<
    GateFactory,
    Gate,
    ArithmeticFactory,
    SqrtFactory,
>(
    handoff: &RestrictedSourceSetHandoff,
    frame_values: &CanonicalSourceSetFrameValues,
    mut gate_factory: GateFactory,
    mut arithmetic_factory: ArithmeticFactory,
    mut sqrt_factory: SqrtFactory,
) -> Result<CanonicalSourceSetPlacement, CanonicalSourceSetPlacementError>
where
    GateFactory: FnMut(&SourceSetMemberKey, SourceSetMemberRole) -> Gate,
    Gate: QuaternionNormalizationGate,
    ArithmeticFactory: FnMut(
        &SourceSetMemberKey,
        SourceSetMemberRole,
    ) -> Option<Box<dyn Binary64ArithmeticProvider>>,
    SqrtFactory:
        FnMut(&SourceSetMemberKey, SourceSetMemberRole) -> Option<Box<dyn CorrectlyRoundedSqrt>>,
{
    // Complete boundary validation, including every successful value's inner
    // identity, happens before the first factory can be acquired.
    validate_source_set_boundary(handoff, frame_values)?;

    let mut members = BTreeMap::new();
    for (key, member) in handoff.members() {
        let Some(values_entry) = frame_values.members().get(key) else {
            // Keep the operation total even if this helper is later reused
            // without the current validation call at its entry.
            return Err(CanonicalSourceSetPlacementError::MissingCanonicalMember {
                member: key.clone(),
            });
        };
        let role = member.role();
        let canonical_frame_values = values_entry.result().clone();

        let placement = match &canonical_frame_values {
            Err(_) => None,
            Ok(values) => {
                let mut gate = gate_factory(key, role);
                let mut arithmetic_provider = arithmetic_factory(key, role);
                let mut arithmetic_capability = match arithmetic_provider.as_deref_mut() {
                    Some(provider) => Binary64ArithmeticCapability::provided(provider),
                    None => Binary64ArithmeticCapability::unavailable(),
                };
                let mut sqrt_provider = sqrt_factory(key, role);
                let mut sqrt_capability = match sqrt_provider.as_deref_mut() {
                    Some(provider) => SqrtCapability::provided(provider),
                    None => SqrtCapability::unavailable(),
                };
                Some(prepare_canonical_member_placement(
                    member,
                    values,
                    &mut gate,
                    &mut arithmetic_capability,
                    &mut sqrt_capability,
                ))
            }
        };

        members.insert(
            key.clone(),
            CanonicalSourceSetMemberPlacementResult {
                role,
                canonical_frame_values,
                placement,
            },
        );
    }

    Ok(CanonicalSourceSetPlacement {
        root: handoff.root().clone(),
        members,
    })
}

fn validate_source_set_boundary(
    handoff: &RestrictedSourceSetHandoff,
    frame_values: &CanonicalSourceSetFrameValues,
) -> Result<(), CanonicalSourceSetPlacementError> {
    if handoff.root() != frame_values.root() {
        return Err(CanonicalSourceSetPlacementError::RootMismatch {
            handoff_root: handoff.root().clone(),
            values_root: frame_values.root().clone(),
        });
    }

    for (key, member) in handoff.members() {
        let Some(values) = frame_values.members().get(key) else {
            return Err(CanonicalSourceSetPlacementError::MissingCanonicalMember {
                member: key.clone(),
            });
        };
        if values.role() != member.role() {
            return Err(CanonicalSourceSetPlacementError::MemberRoleMismatch {
                member: key.clone(),
                handoff_role: member.role(),
                values_role: values.role(),
            });
        }
        if let Ok(values) = values.result() {
            validate_canonical_value_identity(key, member.role(), values)?;
        }
    }

    let handoff_keys = handoff.members().keys().collect::<BTreeSet<_>>();
    for key in frame_values.members().keys() {
        if !handoff_keys.contains(key) {
            return Err(
                CanonicalSourceSetPlacementError::UnexpectedCanonicalMember {
                    member: key.clone(),
                },
            );
        }
    }
    Ok(())
}

fn validate_canonical_value_identity(
    member: &SourceSetMemberKey,
    expected_role: SourceSetMemberRole,
    values: &CanonicalMemberFrameValues,
) -> Result<(), CanonicalSourceSetPlacementError> {
    if values.member() != member || values.role() != expected_role {
        return Err(
            CanonicalSourceSetPlacementError::CanonicalValueIdentityMismatch {
                member: member.clone(),
                values_member: values.member().clone(),
                expected_role,
                values_role: values.role(),
            },
        );
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::body_document::ResourceProfile;
    use crate::canonical_member_frame_values::CanonicalMemberValueSlot;
    use crate::quaternion_normalization::{
        Binary64ArithmeticProviderFailure, GateRejection, SqrtProviderFailure,
    };
    use crate::restricted_source_set_handoff::build_restricted_source_set_handoff;
    use crate::source_set_canonical_values::prepare_canonical_source_set_frame_values;
    use crate::source_set_preparation::{SourceSetInput, prepare_source_set};
    use std::cell::RefCell;
    use std::rc::Rc;

    const SOURCE: &[u8] =
        include_bytes!("../../../examples/body-documents/stylized-digitigrade-biped.json");

    #[derive(Default)]
    struct NativeArithmetic;

    impl Binary64ArithmeticProvider for NativeArithmetic {
        fn add(&mut self, left: f64, right: f64) -> Result<f64, Binary64ArithmeticProviderFailure> {
            Ok(left + right)
        }

        fn sub(&mut self, left: f64, right: f64) -> Result<f64, Binary64ArithmeticProviderFailure> {
            Ok(left - right)
        }

        fn mul(&mut self, left: f64, right: f64) -> Result<f64, Binary64ArithmeticProviderFailure> {
            Ok(left * right)
        }

        fn div(&mut self, left: f64, right: f64) -> Result<f64, Binary64ArithmeticProviderFailure> {
            Ok(left / right)
        }
    }

    struct NativeSqrt;

    impl CorrectlyRoundedSqrt for NativeSqrt {
        fn sqrt(&mut self, input: f64) -> Result<f64, SqrtProviderFailure> {
            Ok(input.sqrt())
        }
    }

    #[derive(Default)]
    struct AllowGate;

    impl QuaternionNormalizationGate for AllowGate {
        fn validate_input(&mut self, _components: [f64; 4]) -> Result<(), GateRejection> {
            Ok(())
        }

        fn validate_scaled_norm(&mut self, _squared_norm: f64) -> Result<(), GateRejection> {
            Ok(())
        }

        fn validate_output(&mut self, _components: [f64; 4]) -> Result<(), GateRejection> {
            Ok(())
        }
    }

    struct SelectiveGate {
        reject: bool,
    }

    impl QuaternionNormalizationGate for SelectiveGate {
        fn validate_input(&mut self, _components: [f64; 4]) -> Result<(), GateRejection> {
            (!self.reject).then_some(()).ok_or(GateRejection::Rejected)
        }

        fn validate_scaled_norm(&mut self, _squared_norm: f64) -> Result<(), GateRejection> {
            (!self.reject).then_some(()).ok_or(GateRejection::Rejected)
        }

        fn validate_output(&mut self, _components: [f64; 4]) -> Result<(), GateRejection> {
            (!self.reject).then_some(()).ok_or(GateRejection::Rejected)
        }
    }

    fn source(document: &str, namespace: &str) -> Vec<u8> {
        let mut value: serde_json::Value = serde_json::from_slice(SOURCE).unwrap();
        value["source"]["document"] = serde_json::Value::String(document.to_owned());
        value["source"]["namespace"] = serde_json::Value::String(namespace.to_owned());
        rewrite_namespaces(&mut value["body"], namespace);
        value["source"]["dependencies"] = serde_json::Value::Array(Vec::new());
        serde_json::to_vec(&value).unwrap()
    }

    fn rewrite_namespaces(value: &mut serde_json::Value, namespace: &str) {
        match value {
            serde_json::Value::Object(object) => {
                if object.contains_key("namespace") {
                    object.insert(
                        "namespace".to_owned(),
                        serde_json::Value::String(namespace.to_owned()),
                    );
                }
                for child in object.values_mut() {
                    rewrite_namespaces(child, namespace);
                }
            }
            serde_json::Value::Array(array) => {
                for child in array {
                    rewrite_namespaces(child, namespace);
                }
            }
            _ => {}
        }
    }

    fn handoff<'a>(root: &'a [u8], dependencies: Vec<&'a [u8]>) -> RestrictedSourceSetHandoff {
        let prepared = prepare_source_set(SourceSetInput::new(
            root,
            dependencies,
            ResourceProfile::ORDINARY,
        ))
        .unwrap();
        build_restricted_source_set_handoff(Ok(prepared)).unwrap()
    }

    fn canonical_values(set: &RestrictedSourceSetHandoff) -> CanonicalSourceSetFrameValues {
        prepare_canonical_source_set_frame_values(
            set,
            |_key, _role| AllowGate,
            |_key, _role| Some(Box::new(NativeArithmetic)),
            |_key, _role| Some(Box::new(NativeSqrt)),
        )
    }

    fn placement(
        set: &RestrictedSourceSetHandoff,
        values: &CanonicalSourceSetFrameValues,
    ) -> CanonicalSourceSetPlacement {
        prepare_canonical_source_set_placement(
            set,
            values,
            |_key, _role| AllowGate,
            |_key, _role| Some(Box::new(NativeArithmetic)),
            |_key, _role| Some(Box::new(NativeSqrt)),
        )
        .unwrap()
    }

    #[test]
    fn root_and_dependency_retain_identity_role_and_representative_outputs() {
        let root = source("root_doc", "root_ns");
        let dependency = source("dependency_doc", "dependency_ns");
        let set = handoff(&root, vec![&dependency]);
        let values = canonical_values(&set);
        let output = placement(&set, &values);

        assert_eq!(output.root(), set.root());
        assert_eq!(output.members().len(), 2);
        for (key, entry) in output.members() {
            assert_eq!(entry.role(), set.members()[key].role());
            assert!(entry.canonical_frame_values().is_ok());
            let result = entry
                .placement()
                .expect("upstream success attempts placement");
            let placed = result.as_ref().expect("representative placement succeeds");
            assert_eq!(placed.member(), key);
            assert_eq!(placed.role(), entry.role());
            assert!(!placed.parts().is_empty());
            assert!(!placed.attachments().is_empty());
        }
    }

    #[test]
    fn upstream_failure_is_retained_and_skips_placement_capabilities_for_that_member() {
        let root = source("root_doc", "root_ns");
        let dependency = source("dependency_doc", "dependency_ns");
        let set = handoff(&root, vec![&dependency]);
        let values = prepare_canonical_source_set_frame_values(
            &set,
            |_key, _role| AllowGate,
            |_key, _role| Some(Box::new(NativeArithmetic)),
            |key, _role| {
                (key.document() == "root_doc")
                    .then(|| Box::new(NativeSqrt) as Box<dyn CorrectlyRoundedSqrt>)
            },
        );
        let trace = Rc::new(RefCell::new(Vec::<SourceSetMemberKey>::new()));
        let output = prepare_canonical_source_set_placement(
            &set,
            &values,
            {
                let trace = Rc::clone(&trace);
                move |key, _role| {
                    trace.borrow_mut().push(key.clone());
                    AllowGate
                }
            },
            {
                let trace = Rc::clone(&trace);
                move |key, _role| {
                    trace.borrow_mut().push(key.clone());
                    Some(Box::new(NativeArithmetic) as Box<dyn Binary64ArithmeticProvider>)
                }
            },
            {
                let trace = Rc::clone(&trace);
                move |key, _role| {
                    trace.borrow_mut().push(key.clone());
                    Some(Box::new(NativeSqrt) as Box<dyn CorrectlyRoundedSqrt>)
                }
            },
        )
        .unwrap();

        let failed = output
            .members()
            .values()
            .find(|entry| entry.role() == SourceSetMemberRole::Dependency)
            .unwrap();
        assert!(matches!(
            failed.canonical_frame_values(),
            Err(CanonicalMemberFrameValuesError::QuaternionNormalization { location, .. })
                if matches!(location.slot(), CanonicalMemberValueSlot::PartPlacement { .. })
        ));
        assert!(failed.placement().is_none());
        let successful_key = output.root().clone();
        assert_eq!(
            trace.borrow().as_slice(),
            &[
                successful_key.clone(),
                successful_key.clone(),
                successful_key.clone()
            ]
        );
        assert!(
            output.members()[&successful_key]
                .placement()
                .unwrap()
                .is_ok()
        );
    }

    #[test]
    fn placement_failure_is_member_local_and_other_member_still_completes() {
        let root = source("root_doc", "root_ns");
        let dependency = source("dependency_doc", "dependency_ns");
        let set = handoff(&root, vec![&dependency]);
        let values = canonical_values(&set);
        let output = prepare_canonical_source_set_placement(
            &set,
            &values,
            |key, _role| SelectiveGate {
                reject: key.document() == "dependency_doc",
            },
            |_key, _role| Some(Box::new(NativeArithmetic)),
            |_key, _role| Some(Box::new(NativeSqrt)),
        )
        .unwrap();

        let root_result = output.members()[output.root()].placement().unwrap();
        assert!(root_result.is_ok());
        let dependency = output
            .members()
            .values()
            .find(|entry| entry.role() == SourceSetMemberRole::Dependency)
            .unwrap();
        assert!(dependency.canonical_frame_values().is_ok());
        assert!(matches!(
            dependency.placement(),
            Some(Err(CanonicalMemberPlacementError::Arithmetic { .. }))
        ));
    }

    #[test]
    fn source_set_boundary_mismatches_are_typed() {
        let root = source("root_doc", "root_ns");
        let dependency = source("dependency_doc", "dependency_ns");
        let other_dependency = source("other_dependency_doc", "other_dependency_ns");
        let first = handoff(&root, vec![&dependency]);
        let second = handoff(&root, vec![&other_dependency]);
        let first_values = canonical_values(&first);
        let error = prepare_canonical_source_set_placement(
            &second,
            &first_values,
            |_key, _role| AllowGate,
            |_key, _role| Some(Box::new(NativeArithmetic)),
            |_key, _role| Some(Box::new(NativeSqrt)),
        )
        .unwrap_err();
        assert!(matches!(
            error,
            CanonicalSourceSetPlacementError::MissingCanonicalMember { .. }
        ));

        let single_member = handoff(&root, vec![]);
        let error = prepare_canonical_source_set_placement(
            &single_member,
            &first_values,
            |_key, _role| AllowGate,
            |_key, _role| Some(Box::new(NativeArithmetic)),
            |_key, _role| Some(Box::new(NativeSqrt)),
        )
        .unwrap_err();
        assert!(matches!(
            error,
            CanonicalSourceSetPlacementError::UnexpectedCanonicalMember { .. }
        ));

        let other_root = source("other_root_doc", "other_root_ns");
        let other_set = handoff(&other_root, vec![&dependency]);
        let other_values = canonical_values(&other_set);
        let error = prepare_canonical_source_set_placement(
            &first,
            &other_values,
            |_key, _role| AllowGate,
            |_key, _role| Some(Box::new(NativeArithmetic)),
            |_key, _role| Some(Box::new(NativeSqrt)),
        )
        .unwrap_err();
        assert!(matches!(
            error,
            CanonicalSourceSetPlacementError::RootMismatch { .. }
        ));
    }

    #[test]
    fn canonical_value_identity_preflight_rejects_key_and_role_mutations() {
        let root = source("root_doc", "root_ns");
        let dependency = source("dependency_doc", "dependency_ns");
        let set = handoff(&root, vec![&dependency]);
        let values = canonical_values(&set);
        let root_values = values
            .members()
            .get(values.root())
            .unwrap()
            .result()
            .as_ref()
            .unwrap();
        let dependency_key = set.members().keys().find(|key| *key != set.root()).unwrap();

        // The production coordinator runs this identity seam for every
        // successful map entry before acquiring any placement capability.
        let error = validate_canonical_value_identity(
            dependency_key,
            SourceSetMemberRole::Dependency,
            root_values,
        )
        .unwrap_err();
        assert!(matches!(
            error,
            CanonicalSourceSetPlacementError::CanonicalValueIdentityMismatch { .. }
        ));

        let error = validate_canonical_value_identity(
            set.root(),
            SourceSetMemberRole::Dependency,
            root_values,
        )
        .unwrap_err();
        assert!(matches!(
            error,
            CanonicalSourceSetPlacementError::CanonicalValueIdentityMismatch { .. }
        ));
    }

    #[test]
    fn unavailable_capability_is_retained_as_member_local_placement_failure() {
        let root = source("root_doc", "root_ns");
        let dependency = source("dependency_doc", "dependency_ns");
        let set = handoff(&root, vec![&dependency]);
        let values = canonical_values(&set);
        let output = prepare_canonical_source_set_placement(
            &set,
            &values,
            |_key, _role| AllowGate,
            |_key, _role| None,
            |_key, _role| None,
        )
        .unwrap();
        for entry in output.members().values() {
            assert!(matches!(
                entry.placement(),
                Some(Err(CanonicalMemberPlacementError::Arithmetic { .. }))
            ));
        }
    }

    #[test]
    fn sqrt_unavailable_is_member_local_when_arithmetic_is_available() {
        let root = source("root_doc", "root_ns");
        let dependency = source("dependency_doc", "dependency_ns");
        let set = handoff(&root, vec![&dependency]);
        let values = canonical_values(&set);
        let output = prepare_canonical_source_set_placement(
            &set,
            &values,
            |_key, _role| AllowGate,
            |_key, _role| Some(Box::new(NativeArithmetic)),
            |key, _role| {
                (key.document() == "root_doc")
                    .then(|| Box::new(NativeSqrt) as Box<dyn CorrectlyRoundedSqrt>)
            },
        )
        .unwrap();

        assert!(output.members()[output.root()].placement().unwrap().is_ok());
        let dependency = output
            .members()
            .values()
            .find(|entry| entry.role() == SourceSetMemberRole::Dependency)
            .unwrap();
        assert!(matches!(
            dependency.placement(),
            Some(Err(CanonicalMemberPlacementError::Arithmetic {
                error:
                    crate::quaternion_normalization::QuaternionNormalizationError::SqrtUnavailable,
                ..
            }))
        ));
    }

    #[test]
    fn member_key_order_controls_factory_order_and_output_independent_of_input_order() {
        let root = source("root_doc", "root_ns");
        let first = source("dependency_a", "a_ns");
        let second = source("dependency_b", "b_ns");
        let first_set = handoff(&root, vec![&second, &first]);
        let second_set = handoff(&root, vec![&first, &second]);
        let first_values = canonical_values(&first_set);
        let second_values = canonical_values(&second_set);

        let run = |set: &RestrictedSourceSetHandoff, values: &CanonicalSourceSetFrameValues| {
            let trace = Rc::new(RefCell::new(
                Vec::<(&'static str, SourceSetMemberKey)>::new(),
            ));
            let result = prepare_canonical_source_set_placement(
                set,
                values,
                {
                    let trace = Rc::clone(&trace);
                    move |key, _role| {
                        trace.borrow_mut().push(("gate", key.clone()));
                        AllowGate
                    }
                },
                {
                    let trace = Rc::clone(&trace);
                    move |key, _role| {
                        trace.borrow_mut().push(("arithmetic", key.clone()));
                        Some(Box::new(NativeArithmetic) as Box<dyn Binary64ArithmeticProvider>)
                    }
                },
                {
                    let trace = Rc::clone(&trace);
                    move |key, _role| {
                        trace.borrow_mut().push(("sqrt", key.clone()));
                        Some(Box::new(NativeSqrt) as Box<dyn CorrectlyRoundedSqrt>)
                    }
                },
            )
            .unwrap();
            (result, trace.borrow().clone())
        };

        let (first_output, first_trace) = run(&first_set, &first_values);
        let (second_output, second_trace) = run(&second_set, &second_values);
        assert_eq!(first_output, second_output);
        assert_eq!(first_trace, second_trace);
    }
}
