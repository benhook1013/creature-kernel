//! Crate-private, owned handoff for an already prepared source set.
//!
//! This is a narrow bridge between the existing source-set preparation
//! projection and a future resolver/snapshot transaction.  It owns the raw
//! bytes and prepared projections for every admitted member, while retaining
//! only locator-level dependency outcomes.  It does not acquire or verify
//! dependencies, merge namespaces, resolve references, or claim a snapshot.

#![allow(dead_code)]

use crate::source_preparation::PreparedSingleSource;
use crate::source_set_preparation::{
    PreparedSourceSet, SourceSetDependencyLocatorResult, SourceSetMemberKey, SourceSetMemberRole,
    SourceSetPreparationError,
};
use std::collections::BTreeMap;
use std::fmt;

/// One fully owned member retained by the restricted handoff.
///
/// The prepared source remains a source-linked projection.  Owning it here
/// does not turn it into a canonical semantic record or a resolved member.
#[derive(Clone, Debug)]
pub(crate) struct RestrictedSourceSetMember {
    key: SourceSetMemberKey,
    role: SourceSetMemberRole,
    raw_source: Vec<u8>,
    prepared_source: PreparedSingleSource,
}

impl RestrictedSourceSetMember {
    /// Stable admitted `(document, namespace)` member key.
    #[must_use]
    pub(crate) fn key(&self) -> &SourceSetMemberKey {
        &self.key
    }

    /// Explicit root or supplied-dependency role.
    #[must_use]
    pub(crate) const fn role(&self) -> SourceSetMemberRole {
        self.role
    }

    /// Exact source bytes supplied for this member.
    #[must_use]
    pub(crate) fn raw_source(&self) -> &[u8] {
        &self.raw_source
    }

    /// Owned prepared source/provenance projection.
    #[must_use]
    pub(crate) fn prepared_source(&self) -> &PreparedSingleSource {
        &self.prepared_source
    }
}

/// Failure while constructing the owned restricted source-set handoff.
///
/// A preparation error is propagated before any handoff is returned.  The
/// invariant variant is reserved for an impossible violation in the existing
/// prepared-set contract and is not mapped to a resolver status here.
#[derive(Debug, PartialEq)]
pub(crate) enum RestrictedSourceSetHandoffError {
    /// The upstream source-set preparation did not produce a complete set.
    Preparation(SourceSetPreparationError),
    /// The existing prepared-set projection violated its internal contract.
    Invariant { condition: &'static str },
}

impl fmt::Display for RestrictedSourceSetHandoffError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Preparation(error) => write!(formatter, "source-set preparation failed: {error}"),
            Self::Invariant { condition } => {
                write!(
                    formatter,
                    "prepared source-set invariant failed: {condition}"
                )
            }
        }
    }
}

impl std::error::Error for RestrictedSourceSetHandoffError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::Preparation(error) => Some(error),
            Self::Invariant { .. } => None,
        }
    }
}

/// Fully owned, deterministic, non-resolving source-set handoff.
///
/// Members are keyed by their admitted source `(document, namespace)`.  The
/// dependency results retain each complete declaration and classify only
/// whether its locator names another supplied member.  Revision/hash text is
/// opaque intent for a later resolver; it is not verified here.
#[derive(Clone, Debug)]
pub(crate) struct RestrictedSourceSetHandoff {
    root: SourceSetMemberKey,
    members: BTreeMap<SourceSetMemberKey, RestrictedSourceSetMember>,
    dependency_locator_results: Vec<SourceSetDependencyLocatorResult>,
}

impl RestrictedSourceSetHandoff {
    /// Stable key of the designated root member.
    #[must_use]
    pub(crate) fn root(&self) -> &SourceSetMemberKey {
        &self.root
    }

    /// Deterministically keyed, fully owned members.
    #[must_use]
    pub(crate) fn members(&self) -> &BTreeMap<SourceSetMemberKey, RestrictedSourceSetMember> {
        &self.members
    }

    /// Deterministically ordered declared-edge locator outcomes.
    ///
    /// `SuppliedTarget` means only that the declaration locator matched an
    /// admitted member key.  It does not imply revision/hash verification or
    /// successful dependency resolution.
    #[must_use]
    pub(crate) fn dependency_locator_results(&self) -> &[SourceSetDependencyLocatorResult] {
        &self.dependency_locator_results
    }
}

/// Construct the owned handoff from the existing source-set preparation
/// result.
///
/// The coordinator consumes the upstream `Result` rather than admitting or
/// preparing source bytes itself.  Consequently malformed input, invalid
/// members, duplicate keys, and all other upstream failures return without a
/// partial handoff.  Successful construction copies raw bytes and moves the
/// prepared projections into owned records after validating the small contract
/// needed by this bridge.
pub(crate) fn build_restricted_source_set_handoff(
    prepared: Result<PreparedSourceSet<'_>, SourceSetPreparationError>,
) -> Result<RestrictedSourceSetHandoff, RestrictedSourceSetHandoffError> {
    let prepared = prepared.map_err(RestrictedSourceSetHandoffError::Preparation)?;
    validate_prepared_source_set(&prepared)?;

    let (root, prepared_members, dependency_edges) = prepared.into_parts();
    let members = prepared_members
        .into_iter()
        .map(|(map_key, member)| {
            let (key, role, raw_source, prepared_source) = member.into_parts();
            (
                map_key,
                RestrictedSourceSetMember {
                    key,
                    role,
                    raw_source: raw_source.to_vec(),
                    prepared_source,
                },
            )
        })
        .collect::<BTreeMap<_, _>>();
    let dependency_locator_results = dependency_edges
        .into_iter()
        .map(|edge| {
            let target = edge.locator_key();
            if members.contains_key(&target) {
                SourceSetDependencyLocatorResult::SuppliedTarget { edge, target }
            } else {
                SourceSetDependencyLocatorResult::MissingSuppliedTarget { edge }
            }
        })
        .collect();

    Ok(RestrictedSourceSetHandoff {
        root,
        members,
        dependency_locator_results,
    })
}

fn validate_prepared_source_set(
    prepared: &PreparedSourceSet<'_>,
) -> Result<(), RestrictedSourceSetHandoffError> {
    let root_member = prepared.members().get(prepared.root()).ok_or(
        RestrictedSourceSetHandoffError::Invariant {
            condition: "root key must identify a member",
        },
    )?;
    if root_member.role() != SourceSetMemberRole::Root {
        return Err(RestrictedSourceSetHandoffError::Invariant {
            condition: "root member must have root role",
        });
    }

    let root_count = prepared
        .members()
        .values()
        .filter(|member| member.role() == SourceSetMemberRole::Root)
        .count();
    if root_count != 1 {
        return Err(RestrictedSourceSetHandoffError::Invariant {
            condition: "exactly one member must have root role",
        });
    }

    for (key, member) in prepared.members() {
        if member.key() != key {
            return Err(RestrictedSourceSetHandoffError::Invariant {
                condition: "member map key must equal member identity key",
            });
        }
        if member.role() == SourceSetMemberRole::Root && key != prepared.root() {
            return Err(RestrictedSourceSetHandoffError::Invariant {
                condition: "only the root key may have root role",
            });
        }
        if member.role() == SourceSetMemberRole::Dependency && key == prepared.root() {
            return Err(RestrictedSourceSetHandoffError::Invariant {
                condition: "root key may not have dependency role",
            });
        }
    }

    if prepared
        .dependency_edges()
        .iter()
        .any(|edge| !prepared.members().contains_key(edge.owner()))
    {
        return Err(RestrictedSourceSetHandoffError::Invariant {
            condition: "every declared edge owner must be an admitted member",
        });
    }

    if !prepared
        .dependency_edges()
        .windows(2)
        .all(|pair| pair[0] <= pair[1])
    {
        return Err(RestrictedSourceSetHandoffError::Invariant {
            condition: "declared dependency edges must be deterministically sorted",
        });
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::body_document::ResourceProfile;
    use crate::source_set_preparation::{SourceSetInput, SourceSetMemberLocation};
    use serde_json::Value;

    fn source(document: &str, namespace: &str) -> Vec<u8> {
        let mut value: Value = serde_json::from_slice(include_bytes!(
            "../../../examples/body-documents/stylized-digitigrade-biped.json"
        ))
        .expect("example source is valid JSON");
        value["source"]["document"] = Value::String(document.to_owned());
        value["source"]["namespace"] = Value::String(namespace.to_owned());
        rewrite_namespaces(&mut value["body"], namespace);
        value["source"]["dependencies"] = Value::Array(Vec::new());
        serde_json::to_vec(&value).expect("source serializes")
    }

    fn rewrite_namespaces(value: &mut Value, namespace: &str) {
        match value {
            Value::Object(object) => {
                if object.contains_key("namespace") {
                    object.insert("namespace".to_owned(), Value::String(namespace.to_owned()));
                }
                for child in object.values_mut() {
                    rewrite_namespaces(child, namespace);
                }
            }
            Value::Array(array) => {
                for child in array {
                    rewrite_namespaces(child, namespace);
                }
            }
            _ => {}
        }
    }

    fn with_dependencies(source: &[u8], dependencies: Value) -> Vec<u8> {
        let mut value: Value = serde_json::from_slice(source).expect("source is valid JSON");
        value["source"]["dependencies"] = dependencies;
        serde_json::to_vec(&value).expect("source serializes")
    }

    fn declaration(document: &str, namespace: &str, marker: char) -> Value {
        serde_json::json!({
            "document": document,
            "namespace": namespace,
            "content_sha256": format!("sha256:{}", marker.to_string().repeat(64)),
        })
    }

    fn prepared<'a>(
        root: &'a [u8],
        dependencies: Vec<&'a [u8]>,
    ) -> Result<RestrictedSourceSetHandoff, RestrictedSourceSetHandoffError> {
        build_restricted_source_set_handoff(crate::source_set_preparation::prepare_source_set(
            SourceSetInput::new(root, dependencies, ResourceProfile::ORDINARY),
        ))
    }

    #[test]
    fn root_and_located_dependency_are_owned_and_explicitly_classified() {
        let root = with_dependencies(
            &source("root_doc", "root_ns"),
            serde_json::json!([declaration("dep_doc", "dep_ns", 'a')]),
        );
        let dependency = source("dep_doc", "dep_ns");
        let handoff = prepared(&root, vec![&dependency]).expect("handoff succeeds");

        assert_eq!(handoff.root().document(), "root_doc");
        assert_eq!(handoff.members().len(), 2);
        assert_eq!(
            handoff.members()[handoff.root()].role(),
            SourceSetMemberRole::Root
        );
        assert_eq!(
            handoff
                .members()
                .values()
                .find(|member| member.role() == SourceSetMemberRole::Dependency)
                .expect("dependency exists")
                .key()
                .namespace(),
            "dep_ns"
        );
        assert!(matches!(
            &handoff.dependency_locator_results()[0],
            SourceSetDependencyLocatorResult::SuppliedTarget { target, .. }
                if target.document() == "dep_doc" && target.namespace() == "dep_ns"
        ));
    }

    #[test]
    fn missing_target_is_explicit_without_resolution_claim() {
        let root = with_dependencies(
            &source("root_doc", "root_ns"),
            serde_json::json!([declaration("missing_doc", "missing_ns", 'a')]),
        );
        let handoff = prepared(&root, Vec::new()).expect("handoff succeeds");
        assert!(matches!(
            &handoff.dependency_locator_results()[0],
            SourceSetDependencyLocatorResult::MissingSuppliedTarget { .. }
        ));
        assert_eq!(handoff.dependency_locator_results()[0].target(), None);
    }

    #[test]
    fn supplied_member_order_does_not_change_owned_projection() {
        let root = source("root_doc", "root_ns");
        let first_dep = source("dep_a", "a_ns");
        let second_dep = source("dep_b", "b_ns");
        let first = prepared(&root, vec![&first_dep, &second_dep]).expect("handoff succeeds");
        let second = prepared(&root, vec![&second_dep, &first_dep]).expect("handoff succeeds");

        assert_eq!(first.root(), second.root());
        assert_eq!(
            first.members().keys().collect::<Vec<_>>(),
            second.members().keys().collect::<Vec<_>>()
        );
        assert_eq!(
            first.dependency_locator_results(),
            second.dependency_locator_results()
        );
    }

    #[test]
    fn declaration_order_does_not_change_edge_outcomes() {
        let base = source("root_doc", "root_ns");
        let a = declaration("dep_a", "a_ns", 'a');
        let b = declaration("dep_b", "b_ns", 'b');
        let first_bytes = with_dependencies(&base, serde_json::json!([a.clone(), b.clone()]));
        let second_bytes = with_dependencies(&base, serde_json::json!([b, a]));
        let first = prepared(&first_bytes, Vec::new()).expect("handoff succeeds");
        let second = prepared(&second_bytes, Vec::new()).expect("handoff succeeds");

        assert_eq!(
            first.dependency_locator_results(),
            second.dependency_locator_results()
        );
        assert_ne!(
            first.members()[first.root()].raw_source(),
            second.members()[second.root()].raw_source()
        );
    }

    #[test]
    fn duplicate_member_key_is_upstream_failure_with_no_handoff() {
        let root = source("same_doc", "same_ns");
        let duplicate = source("same_doc", "same_ns");
        let error = prepared(&root, vec![&duplicate]).expect_err("duplicate must fail closed");
        assert!(matches!(
            error,
            RestrictedSourceSetHandoffError::Preparation(
                SourceSetPreparationError::DuplicateMemberKey { .. }
            )
        ));
    }

    #[test]
    fn invalid_member_is_upstream_failure_with_no_partial_result() {
        let root = source("root_doc", "root_ns");
        let error = prepared(&root, vec![br"{"]).expect_err("invalid member must fail closed");
        assert!(matches!(
            error,
            RestrictedSourceSetHandoffError::Preparation(SourceSetPreparationError::Member {
                location: SourceSetMemberLocation::SuppliedDependency { position: 0 },
                ..
            })
        ));
    }

    #[test]
    fn opaque_declared_hash_is_retained_unchanged() {
        let declared = format!("sha256:{}", "f".repeat(64));
        let root = with_dependencies(
            &source("root_doc", "root_ns"),
            serde_json::json!([{
                "document": "dep_doc",
                "namespace": "dep_ns",
                "content_sha256": declared,
            }]),
        );
        let dependency = source("dep_doc", "dep_ns");
        let handoff = prepared(&root, vec![&dependency]).expect("handoff succeeds");
        assert_eq!(
            handoff.dependency_locator_results()[0]
                .edge()
                .dependency()
                .content_sha256,
            declared
        );
    }

    #[test]
    fn handoff_owns_raw_bytes_after_input_storage_changes() {
        let mut root = with_dependencies(
            &source("root_doc", "root_ns"),
            serde_json::json!([declaration("dep_doc", "dep_ns", 'a')]),
        );
        let mut dependency = source("dep_doc", "dep_ns");
        let root_before = root.clone();
        let dependency_before = dependency.clone();
        let handoff = prepared(&root, vec![&dependency]).expect("handoff succeeds");
        root.fill(b'x');
        dependency.fill(b'y');

        assert_eq!(handoff.members()[handoff.root()].raw_source(), root_before);
        let dependency_member = handoff
            .members()
            .values()
            .find(|member| member.role() == SourceSetMemberRole::Dependency)
            .expect("dependency exists");
        assert_eq!(dependency_member.raw_source(), dependency_before);
    }
}
