//! Crate-private coordination of independent canonical member preparation.
//!
//! This is a deliberately small source-set bridge over
//! [`crate::canonical_member_frame_values::prepare_canonical_member_frame_values`].
//! It walks the already owned handoff in deterministic member-key order and
//! keeps each member's result isolated.  Gate and square-root state are
//! supplied by the caller for every member; this module selects no defaults,
//! providers, constants, status, or aggregate validity semantics.

#![allow(dead_code)]

use crate::canonical_member_frame_values::{
    CanonicalMemberFrameValues, CanonicalMemberFrameValuesError,
    prepare_canonical_member_frame_values,
};
use crate::quaternion_normalization::{
    Binary64ArithmeticCapability, Binary64ArithmeticProvider, CorrectlyRoundedSqrt,
    QuaternionNormalizationGate, SqrtCapability,
};
use crate::restricted_source_set_handoff::RestrictedSourceSetHandoff;
use crate::source_set_preparation::{SourceSetMemberKey, SourceSetMemberRole};
use std::collections::BTreeMap;

/// The independently retained canonical result for one admitted member.
///
/// The result is retained even when preparation fails.  A failure for one
/// member therefore cannot suppress another admitted member or turn this
/// record into an aggregate status.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct CanonicalSourceSetMemberResult {
    role: SourceSetMemberRole,
    result: Result<CanonicalMemberFrameValues, CanonicalMemberFrameValuesError>,
}

impl CanonicalSourceSetMemberResult {
    /// Root/dependency role retained from the handoff.
    #[must_use]
    pub(crate) const fn role(&self) -> SourceSetMemberRole {
        self.role
    }

    /// Independent canonical preparation result for this member.
    pub(crate) fn result(
        &self,
    ) -> &Result<CanonicalMemberFrameValues, CanonicalMemberFrameValuesError> {
        &self.result
    }
}

/// Owned per-member canonical preparation results for one source-set handoff.
///
/// Member keys remain the source-local `(document, namespace)` keys from the
/// handoff.  This is not a namespace projection, transform composition,
/// resolved snapshot, aggregate status, or public/wire contract.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct CanonicalSourceSetFrameValues {
    root: SourceSetMemberKey,
    members: BTreeMap<SourceSetMemberKey, CanonicalSourceSetMemberResult>,
}

impl CanonicalSourceSetFrameValues {
    /// Source-set root key retained unchanged from the handoff.
    #[must_use]
    pub(crate) fn root(&self) -> &SourceSetMemberKey {
        &self.root
    }

    /// Deterministically keyed result for every admitted member.
    #[must_use]
    pub(crate) fn members(&self) -> &BTreeMap<SourceSetMemberKey, CanonicalSourceSetMemberResult> {
        &self.members
    }
}

/// Prepare every admitted source-set member independently.
///
/// The handoff's `BTreeMap` order is the only coordinator order. The gate and
/// arithmetic factories are called exactly once per member and must return
/// fresh state. The arithmetic factory is called before the square-root
/// factory. The square-root factory is likewise called exactly once per member and
/// returns either a fresh explicitly supplied provider or `None`, which means
/// that member receives an explicitly unavailable capability. Neither factory
/// has a failure channel: the unavailable capability is the only provider
/// absence represented here. Provider state is not shared across members.
///
/// Every member receives a result record, including failures.  The operation
/// does not stop after a member failure and does not calculate an aggregate
/// status or validity result.
pub(crate) fn prepare_canonical_source_set_frame_values<
    GateFactory,
    Gate,
    ArithmeticFactory,
    SqrtFactory,
>(
    handoff: &RestrictedSourceSetHandoff,
    mut gate_factory: GateFactory,
    mut arithmetic_factory: ArithmeticFactory,
    mut sqrt_factory: SqrtFactory,
) -> CanonicalSourceSetFrameValues
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
    let members = handoff
        .members()
        .iter()
        .map(|(key, member)| {
            let role = member.role();
            let mut gate = gate_factory(key, role);
            let mut arithmetic_provider = arithmetic_factory(key, role);
            let mut arithmetic_capability = match arithmetic_provider.as_deref_mut() {
                Some(provider) => Binary64ArithmeticCapability::provided(provider),
                None => Binary64ArithmeticCapability::unavailable(),
            };
            let mut provider = sqrt_factory(key, role);
            let mut capability = match provider.as_deref_mut() {
                Some(provider) => SqrtCapability::provided(provider),
                None => SqrtCapability::unavailable(),
            };
            let result = prepare_canonical_member_frame_values(
                member,
                &mut gate,
                &mut arithmetic_capability,
                &mut capability,
            );
            (key.clone(), CanonicalSourceSetMemberResult { role, result })
        })
        .collect();

    CanonicalSourceSetFrameValues {
        root: handoff.root().clone(),
        members,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::body_document::ResourceProfile;
    use crate::canonical_member_frame_values::CanonicalMemberValueSlot;
    use crate::frame::{Handedness, LengthUnit, SignedAxis, SourceBasis};
    use crate::quaternion_normalization::{
        Binary64ArithmeticProvider, Binary64ArithmeticProviderFailure, CorrectlyRoundedSqrt,
        GateRejection, SqrtProviderFailure,
    };
    use crate::restricted_source_set_handoff::build_restricted_source_set_handoff;
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

    fn native_arithmetic_factory(
        _key: &SourceSetMemberKey,
        _role: SourceSetMemberRole,
    ) -> Option<Box<dyn Binary64ArithmeticProvider>> {
        Some(Box::new(NativeArithmetic))
    }

    #[derive(Default)]
    struct Gate {
        calls: usize,
        reject: bool,
    }

    impl QuaternionNormalizationGate for Gate {
        fn validate_input(&mut self, _components: [f64; 4]) -> Result<(), GateRejection> {
            self.calls += 1;
            if self.reject {
                Err(GateRejection::Rejected)
            } else {
                Ok(())
            }
        }

        fn validate_scaled_norm(&mut self, _squared_norm: f64) -> Result<(), GateRejection> {
            self.calls += 1;
            Ok(())
        }

        fn validate_output(&mut self, _components: [f64; 4]) -> Result<(), GateRejection> {
            self.calls += 1;
            Ok(())
        }
    }

    struct Sqrt {
        trace: Rc<RefCell<Vec<usize>>>,
        member_index: usize,
    }

    impl CorrectlyRoundedSqrt for Sqrt {
        fn sqrt(&mut self, input: f64) -> Result<f64, SqrtProviderFailure> {
            self.trace.borrow_mut().push(self.member_index);
            Ok(input.sqrt())
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

    fn with_dependencies(source: &[u8], dependencies: serde_json::Value) -> Vec<u8> {
        let mut value: serde_json::Value = serde_json::from_slice(source).unwrap();
        value["source"]["dependencies"] = dependencies;
        serde_json::to_vec(&value).unwrap()
    }

    fn with_basis(
        source: &[u8],
        length_unit: &str,
        handedness: &str,
        up: &str,
        forward: &str,
    ) -> Vec<u8> {
        let mut value: serde_json::Value = serde_json::from_slice(source).unwrap();
        value["basis"] = serde_json::json!({
            "length_unit": length_unit,
            "handedness": handedness,
            "up": up,
            "forward": forward,
        });
        serde_json::to_vec(&value).unwrap()
    }

    fn declaration(document: &str, namespace: &str) -> serde_json::Value {
        serde_json::json!({
            "document": document,
            "namespace": namespace,
            "content_sha256": format!("sha256:{}", "a".repeat(64)),
        })
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

    fn prepared_with_two_dependencies() -> (Vec<u8>, Vec<u8>, Vec<u8>) {
        let root = source("root", "root_ns");
        let first = source("dep_a", "a_ns");
        let second = source("dep_b", "b_ns");
        (root, first, second)
    }

    #[test]
    fn every_member_is_prepared_once_in_sorted_key_order_and_roles_are_retained() {
        let (root, first, second) = prepared_with_two_dependencies();
        let set = handoff(&root, vec![&second, &first]);
        let factory_trace = Rc::new(RefCell::new(Vec::new()));
        let provider_trace = Rc::new(RefCell::new(Vec::new()));
        let result = prepare_canonical_source_set_frame_values(
            &set,
            {
                let factory_trace = Rc::clone(&factory_trace);
                move |key: &SourceSetMemberKey, role| {
                    factory_trace.borrow_mut().push(("gate", key.clone(), role));
                    Gate::default()
                }
            },
            {
                let factory_trace = Rc::clone(&factory_trace);
                move |key: &SourceSetMemberKey, role| {
                    factory_trace
                        .borrow_mut()
                        .push(("arithmetic", key.clone(), role));
                    Some(Box::new(NativeArithmetic) as Box<dyn Binary64ArithmeticProvider>)
                }
            },
            {
                let factory_trace = Rc::clone(&factory_trace);
                let provider_trace = Rc::clone(&provider_trace);
                move |key: &SourceSetMemberKey, role| {
                    let index = factory_trace
                        .borrow()
                        .iter()
                        .filter(|(kind, _, _)| *kind == "sqrt")
                        .count();
                    factory_trace.borrow_mut().push(("sqrt", key.clone(), role));
                    Some(Box::new(Sqrt {
                        trace: Rc::clone(&provider_trace),
                        member_index: index,
                    }) as Box<dyn CorrectlyRoundedSqrt>)
                }
            },
        );

        let expected_keys = set.members().keys().cloned().collect::<Vec<_>>();
        assert_eq!(result.root(), set.root());
        assert_eq!(
            result.members().keys().cloned().collect::<Vec<_>>(),
            expected_keys
        );
        let expected_factory_trace = expected_keys
            .iter()
            .flat_map(|key| {
                let role = set.members()[key].role();
                [
                    ("gate", key.clone(), role),
                    ("arithmetic", key.clone(), role),
                    ("sqrt", key.clone(), role),
                ]
            })
            .collect::<Vec<_>>();
        assert_eq!(*factory_trace.borrow(), expected_factory_trace);
        let provider_calls = provider_trace.borrow();
        assert!((0..expected_keys.len()).all(|index| { provider_calls.contains(&index) }));
        assert_eq!(
            result.members()[result.root()].role(),
            SourceSetMemberRole::Root
        );
        assert!(
            result
                .members()
                .values()
                .filter(|member| member.role() == SourceSetMemberRole::Dependency)
                .all(|member| member.result().is_ok())
        );
    }

    #[test]
    fn one_member_failure_does_not_suppress_other_results() {
        let (root, dependency, _) = prepared_with_two_dependencies();
        let set = handoff(&root, vec![&dependency]);
        let result = prepare_canonical_source_set_frame_values(
            &set,
            |key, _| Gate {
                reject: key.document() == "dep_a",
                ..Gate::default()
            },
            native_arithmetic_factory,
            |_key, role| {
                (role == SourceSetMemberRole::Root).then(|| {
                    Box::new(Sqrt {
                        trace: Rc::new(RefCell::new(Vec::new())),
                        member_index: 0,
                    }) as Box<dyn CorrectlyRoundedSqrt>
                })
            },
        );

        assert_eq!(result.members().len(), 2);
        assert!(result.members()[result.root()].result().is_ok());
        let dependency_result = result
            .members()
            .values()
            .find(|member| member.role() == SourceSetMemberRole::Dependency)
            .unwrap();
        assert!(matches!(
            dependency_result.result(),
            Err(crate::canonical_member_frame_values::CanonicalMemberFrameValuesError::QuaternionNormalization {
                location,
                ..
            }) if matches!(location.slot(), CanonicalMemberValueSlot::PartPlacement { .. })
        ));
    }

    #[test]
    fn unavailable_provider_is_explicit_for_selected_member() {
        let (root, dependency, _) = prepared_with_two_dependencies();
        let set = handoff(&root, vec![&dependency]);
        let result = prepare_canonical_source_set_frame_values(
            &set,
            |_key, _role| Gate::default(),
            native_arithmetic_factory,
            |_key, role| {
                (role == SourceSetMemberRole::Root).then(|| {
                    Box::new(Sqrt {
                        trace: Rc::new(RefCell::new(Vec::new())),
                        member_index: 0,
                    }) as Box<dyn CorrectlyRoundedSqrt>
                })
            },
        );

        let dependency_result = result
            .members()
            .values()
            .find(|member| member.role() == SourceSetMemberRole::Dependency)
            .unwrap();
        assert!(matches!(
            dependency_result.result(),
            Err(CanonicalMemberFrameValuesError::QuaternionNormalization {
                error:
                    crate::quaternion_normalization::QuaternionNormalizationError::SqrtUnavailable,
                ..
            })
        ));
    }

    #[test]
    fn reversing_dependency_inputs_preserves_results_and_factory_order() {
        let (root, first, second) = prepared_with_two_dependencies();
        let first_set = handoff(&root, vec![&first, &second]);
        let second_set = handoff(&root, vec![&second, &first]);
        let run = |set: &RestrictedSourceSetHandoff| {
            let trace = Rc::new(RefCell::new(Vec::new()));
            let output = prepare_canonical_source_set_frame_values(
                set,
                {
                    let trace = Rc::clone(&trace);
                    move |key: &SourceSetMemberKey, _| {
                        trace.borrow_mut().push(("gate", key.clone()));
                        Gate::default()
                    }
                },
                native_arithmetic_factory,
                {
                    let trace = Rc::clone(&trace);
                    move |key: &SourceSetMemberKey, _| {
                        trace.borrow_mut().push(("sqrt", key.clone()));
                        Some(Box::new(Sqrt {
                            trace: Rc::new(RefCell::new(Vec::new())),
                            member_index: 0,
                        }) as Box<dyn CorrectlyRoundedSqrt>)
                    }
                },
            );
            (output, trace.borrow().clone())
        };
        let (first_output, first_trace) = run(&first_set);
        let (second_output, second_trace) = run(&second_set);
        assert_eq!(first_output, second_output);
        assert_eq!(first_trace, second_trace);
    }

    #[test]
    fn members_keep_independent_units_bases_and_source_local_keys() {
        let root = source("root", "root_ns");
        let dependency = with_basis(&source("dep", "dep_ns"), "centimetre", "left", "+z", "+x");
        let set = handoff(&root, vec![&dependency]);
        let output = prepare_canonical_source_set_frame_values(
            &set,
            |_key, _role| Gate::default(),
            native_arithmetic_factory,
            |_key, _role| {
                Some(Box::new(Sqrt {
                    trace: Rc::new(RefCell::new(Vec::new())),
                    member_index: 0,
                }) as Box<dyn CorrectlyRoundedSqrt>)
            },
        );

        let dependency_entry = output
            .members()
            .iter()
            .find(|(_, member)| member.role() == SourceSetMemberRole::Dependency)
            .expect("dependency is retained");
        let dependency_values = dependency_entry
            .1
            .result()
            .as_ref()
            .expect("dependency canonicalization succeeds");
        assert_eq!(dependency_values.member(), dependency_entry.0);
        assert_eq!(
            dependency_values.source_basis(),
            SourceBasis::new(
                LengthUnit::Centimetre,
                Handedness::Left,
                SignedAxis::PositiveZ,
                SignedAxis::PositiveX,
            )
            .unwrap()
        );

        let root_values = output
            .members()
            .get(output.root())
            .and_then(|member| member.result().as_ref().ok())
            .expect("root canonicalization succeeds");
        assert_eq!(root_values.source_basis().length_unit(), LengthUnit::Metre);
        let root_torso = root_values
            .parts()
            .iter()
            .find(|(address, _)| address.role() == "torso")
            .map(|(_, transform)| transform.translation().components())
            .expect("root torso exists");
        let dependency_torso = dependency_values
            .parts()
            .iter()
            .find(|(address, _)| address.role() == "torso")
            .map(|(_, transform)| transform.translation().components())
            .expect("dependency torso exists");
        assert_ne!(root_torso, dependency_torso);
    }
}
