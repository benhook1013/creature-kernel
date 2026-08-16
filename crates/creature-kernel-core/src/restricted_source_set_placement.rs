//! Crate-private, source-local exact placement over an admitted source set.
//!
//! This projection evaluates the existing exact Part/Attachment placement
//! operation independently for every member in a
//! [`RestrictedSourceSetHandoff`]. It deliberately does not inspect
//! dependency declarations, acquire or verify dependency content, resolve
//! references across members, merge namespaces, or remap addresses. A local
//! placement error is retained beside the other member results so that one
//! source cannot hide valid placement results from its peers.

#![allow(clippy::result_large_err)]
#![allow(dead_code)]

use crate::reference_placement::{
    ExactReferencePlacements, ReferencePlacementError, resolve_exact_integer_reference_placements,
};
use crate::restricted_source_set_handoff::RestrictedSourceSetHandoff;
use crate::source_set_preparation::{SourceSetMemberKey, SourceSetMemberRole};
use std::collections::BTreeMap;

/// Exact placement result retained for one source-set member.
///
/// The member role is carried independently of the placement result, and the
/// result remains a member-local `Result`: an exact placement failure does not
/// discard or convert any other member's result.
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct RestrictedSourceSetMemberPlacement {
    role: SourceSetMemberRole,
    exact_reference_placements: Result<ExactReferencePlacements, ReferencePlacementError>,
}

impl RestrictedSourceSetMemberPlacement {
    /// Root or supplied-dependency role retained from source-set preparation.
    #[must_use]
    pub(crate) const fn role(&self) -> SourceSetMemberRole {
        self.role
    }

    /// Exact source-local Part/Attachment placement result.
    #[must_use = "inspect the member-local placement result"]
    pub(crate) fn exact_reference_placements(
        &self,
    ) -> &Result<ExactReferencePlacements, ReferencePlacementError> {
        &self.exact_reference_placements
    }
}

/// Deterministic exact-placement projection for every admitted source-set
/// member.
///
/// The root key is retained separately, while member results are keyed by the
/// same admitted `(document, namespace)` keys as the handoff. No member's
/// prepared graph is used while placing another member.
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct RestrictedSourceSetPlacement {
    root: SourceSetMemberKey,
    members: BTreeMap<SourceSetMemberKey, RestrictedSourceSetMemberPlacement>,
}

impl RestrictedSourceSetPlacement {
    /// Stable key of the designated root member.
    #[must_use]
    pub(crate) fn root(&self) -> &SourceSetMemberKey {
        &self.root
    }

    /// Deterministically keyed local placement results for every member.
    #[must_use]
    pub(crate) fn members(
        &self,
    ) -> &BTreeMap<SourceSetMemberKey, RestrictedSourceSetMemberPlacement> {
        &self.members
    }
}

/// Evaluate exact local Part/Attachment placement for every handoff member.
///
/// This function intentionally calls the exact placement operation directly
/// on each prepared source rather than using the restricted single-source
/// snapshot wrapper. Consequently, a member that declares dependencies can
/// still receive its local placement result; declarations remain opaque
/// source intent for later resolution work.
pub(crate) fn build_restricted_source_set_placement(
    handoff: &RestrictedSourceSetHandoff,
) -> RestrictedSourceSetPlacement {
    let members = handoff
        .members()
        .iter()
        .map(|(key, member)| {
            (
                key.clone(),
                RestrictedSourceSetMemberPlacement {
                    role: member.role(),
                    exact_reference_placements: resolve_exact_integer_reference_placements(
                        member.prepared_source(),
                    ),
                },
            )
        })
        .collect();

    RestrictedSourceSetPlacement {
        root: handoff.root().clone(),
        members,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::body_document::ResourceProfile;
    use crate::reference_placement::PlacementSource;
    use crate::restricted_source_set_handoff::build_restricted_source_set_handoff;
    use crate::source_set_preparation::SourceSetInput;
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

    fn handoff<'a>(root: &'a [u8], dependencies: Vec<&'a [u8]>) -> RestrictedSourceSetHandoff {
        build_restricted_source_set_handoff(crate::source_set_preparation::prepare_source_set(
            SourceSetInput::new(root, dependencies, ResourceProfile::ORDINARY),
        ))
        .expect("source-set handoff succeeds")
    }

    fn member<'a>(
        placement: &'a RestrictedSourceSetPlacement,
        document: &str,
        namespace: &str,
    ) -> &'a RestrictedSourceSetMemberPlacement {
        placement
            .members()
            .iter()
            .find(|(key, _)| key.document() == document && key.namespace() == namespace)
            .map(|(_, member)| member)
            .expect("placement member exists")
    }

    #[test]
    fn valid_root_and_supplied_dependency_each_receive_local_placement() {
        let root = with_dependencies(
            &source("root_doc", "root_ns"),
            serde_json::json!([declaration("dep_doc", "dep_ns", 'a')]),
        );
        let dependency = source("dep_doc", "dep_ns");
        let handoff = handoff(&root, vec![&dependency]);
        let placement = build_restricted_source_set_placement(&handoff);

        assert_eq!(placement.root().document(), "root_doc");
        assert_eq!(placement.members().len(), 2);
        assert_eq!(
            member(&placement, "root_doc", "root_ns").role(),
            SourceSetMemberRole::Root
        );
        assert_eq!(
            member(&placement, "dep_doc", "dep_ns").role(),
            SourceSetMemberRole::Dependency
        );
        assert!(
            member(&placement, "root_doc", "root_ns")
                .exact_reference_placements()
                .is_ok()
        );
        assert!(
            member(&placement, "dep_doc", "dep_ns")
                .exact_reference_placements()
                .is_ok()
        );
    }

    #[test]
    fn supplied_input_order_keeps_deterministic_member_key_order_and_results() {
        let root = source("root_doc", "root_ns");
        let dependency_a = source("dep_a", "a_ns");
        let dependency_b = source("dep_b", "b_ns");
        let first_handoff = handoff(&root, vec![&dependency_b, &dependency_a]);
        let second_handoff = handoff(&root, vec![&dependency_a, &dependency_b]);
        let first = build_restricted_source_set_placement(&first_handoff);
        let second = build_restricted_source_set_placement(&second_handoff);

        assert_eq!(first.root(), second.root());
        assert_eq!(
            first.members().keys().collect::<Vec<_>>(),
            second.members().keys().collect::<Vec<_>>()
        );
        assert_eq!(first, second);
    }

    #[test]
    fn local_placement_error_does_not_hide_other_member_result() {
        let root = source("root_doc", "root_ns");
        let mut noncanonical = serde_json::from_slice::<Value>(&source("dep_doc", "dep_ns"))
            .expect("source is valid JSON");
        noncanonical["basis"]["length_unit"] = Value::String("millimetre".to_owned());
        noncanonical["basis"]["handedness"] = Value::String("left".to_owned());
        noncanonical["basis"]["up"] = Value::String("+z".to_owned());
        noncanonical["basis"]["forward"] = Value::String("+x".to_owned());
        let noncanonical = serde_json::to_vec(&noncanonical).expect("source serializes");
        let handoff = handoff(&root, vec![&noncanonical]);
        let placement = build_restricted_source_set_placement(&handoff);

        assert!(
            member(&placement, "root_doc", "root_ns")
                .exact_reference_placements()
                .is_ok()
        );
        assert!(matches!(
            member(&placement, "dep_doc", "dep_ns").exact_reference_placements(),
            Err(crate::reference_placement::ReferencePlacementError::UnsupportedBasis { .. })
        ));
    }

    #[test]
    fn members_are_placed_without_cross_member_address_remapping() {
        let root = source("root_doc", "root_ns");
        let dependency = source("dep_doc", "dep_ns");
        let placement = build_restricted_source_set_placement(&handoff(&root, vec![&dependency]));

        for (document, namespace) in [("root_doc", "root_ns"), ("dep_doc", "dep_ns")] {
            let placements = member(&placement, document, namespace)
                .exact_reference_placements()
                .as_ref()
                .expect("member placement succeeds");
            assert!(
                placements
                    .parts()
                    .keys()
                    .all(|address| address.namespace() == namespace)
            );
            assert!(
                placements
                    .attachments()
                    .keys()
                    .all(|address| address.namespace() == namespace)
            );
        }
    }

    #[test]
    fn declaring_dependencies_does_not_block_local_placement_or_verify_hashes() {
        let root = with_dependencies(
            &source("root_doc", "root_ns"),
            serde_json::json!([{
                "document": "dep_doc",
                "namespace": "dep_ns",
                "content_sha256": format!("sha256:{}", "0".repeat(64)),
            }]),
        );
        let dependency = with_dependencies(
            &source("dep_doc", "dep_ns"),
            serde_json::json!([declaration("unprovided_doc", "unprovided_ns", 'f')]),
        );
        let handoff = handoff(&root, vec![&dependency]);
        let placement = build_restricted_source_set_placement(&handoff);

        assert!(
            member(&placement, "root_doc", "root_ns")
                .exact_reference_placements()
                .is_ok()
        );
        assert!(
            member(&placement, "dep_doc", "dep_ns")
                .exact_reference_placements()
                .is_ok()
        );
        assert_eq!(handoff.dependency_locator_results().len(), 2);
        assert_eq!(
            handoff.dependency_locator_results()[0]
                .edge()
                .dependency()
                .content_sha256,
            format!("sha256:{}", "0".repeat(64))
        );
        assert_eq!(
            handoff.dependency_locator_results()[1]
                .edge()
                .dependency()
                .content_sha256,
            format!("sha256:{}", "f".repeat(64))
        );
    }

    #[test]
    fn attachment_provenance_remains_in_local_result() {
        let root = source("root_doc", "root_ns");
        let placement = build_restricted_source_set_placement(&handoff(&root, Vec::new()));
        let placements = member(&placement, "root_doc", "root_ns")
            .exact_reference_placements()
            .as_ref()
            .expect("example placement succeeds");
        let attached = placements
            .parts()
            .values()
            .find(|part| part.source() == PlacementSource::AuthoredAttachment)
            .expect("example has an attached module root");
        let provenance = attached
            .attachment()
            .expect("attachment provenance retained");
        assert_eq!(provenance.attachment().namespace(), "root_ns");
        assert_eq!(provenance.host_socket().namespace(), "root_ns");
        assert_eq!(provenance.mating_socket().namespace(), "root_ns");
    }
}
