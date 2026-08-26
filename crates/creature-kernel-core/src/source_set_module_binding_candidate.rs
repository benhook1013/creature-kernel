//! Crate-private, non-serialized module-binding candidate evidence.
//!
//! This bridge joins the existing source-set module-binding observation with
//! the caller-profiled dependency-content observation.  It retains source,
//! member, declaration, provenance, cardinality, and instance-root evidence;
//! it does not select a dependency, compare module templates or root roles,
//! derive semantic identity, assign status or diagnostics, or activate R3.

#![allow(dead_code)]

use crate::dependency_content_observation::{
    DependencyContentObservation, observe_dependency_content,
};
use crate::digest::DigestProfile;
use crate::restricted_source_set_handoff::{
    RestrictedSourceSetHandoffError, build_restricted_source_set_handoff,
};
use crate::source_set_module_binding_observation::{
    SourceSetModuleBindingDependency, SourceSetModuleBindingObservation,
    SourceSetModuleBindingRecord, observe_source_set_module_binding,
};
use crate::source_set_preparation::{
    PreparedSourceSet, SourceSetMemberKey, SourceSetPreparationError,
};

/// One owner-authored dependency occurrence joined with its content outcome.
///
/// The dependency occurrence and its provenance are retained from the module
/// observation, and the lower-layer content outcome remains separately typed.
/// Current source admission rejects malformed declared digests before this
/// candidate entrypoint, so the lower-layer `MalformedDeclaredDigest` variant
/// is not reachable candidate evidence.  Current admission also permits at
/// most one owner-authored dependency declaration per namespace; this carrier
/// does not activate duplicate matching-dependency semantics.
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct SourceSetModuleBindingDependencyEvidence {
    dependency: SourceSetModuleBindingDependency,
    content: DependencyContentObservation,
}

impl SourceSetModuleBindingDependencyEvidence {
    /// Owner-authored dependency occurrence and its retained provenance.
    #[must_use]
    pub(crate) fn dependency(&self) -> &SourceSetModuleBindingDependency {
        &self.dependency
    }

    /// Content-only outcome for this exact dependency occurrence.
    #[must_use]
    pub(crate) fn content(&self) -> &DependencyContentObservation {
        &self.content
    }
}

/// One owned module-binding candidate record.
///
/// The complete source-set module-binding observation is retained unchanged
/// in `observation`.  In particular, its supplied-member evidence explicitly
/// distinguishes a missing locator from a supplied member, while its module
/// fields retain optionality, Attachment requirement, root role, and the
/// present instance root and owner-local parent.  `dependencies` retains all
/// currently admitted matching owner-authored evidence in observation order.
/// Its vector shape mirrors the lower-layer observation, but current admission
/// yields zero or one match because it permits at most one dependency
/// declaration per namespace; the shape does not admit future duplicates.
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct SourceSetModuleBindingCandidateRecord {
    observation: SourceSetModuleBindingRecord,
    dependencies: Vec<SourceSetModuleBindingDependencyEvidence>,
}

impl SourceSetModuleBindingCandidateRecord {
    /// Complete owned module-binding ingredient observation.
    #[must_use]
    pub(crate) fn observation(&self) -> &SourceSetModuleBindingRecord {
        &self.observation
    }

    /// Currently admitted matching owner-authored dependency evidence with its
    /// content outcome: zero or one entry under current namespace admission.
    /// The vector does not activate duplicate matching-dependency semantics.
    #[must_use]
    pub(crate) fn dependencies(&self) -> &[SourceSetModuleBindingDependencyEvidence] {
        &self.dependencies
    }
}

/// Owned, deterministic module-binding candidate evidence for one source set.
///
/// This is a pre-Readiness-3 candidate closure, not a semantic binding or
/// resolved graph.  Records are retained in the deterministic order of the
/// existing module-binding observation, and the designated root is copied from
/// the owned source-set handoff.
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct SourceSetModuleBindingCandidate {
    root: SourceSetMemberKey,
    records: Vec<SourceSetModuleBindingCandidateRecord>,
}

impl SourceSetModuleBindingCandidate {
    /// Designated source-set root retained unchanged.
    #[must_use]
    pub(crate) fn root(&self) -> &SourceSetMemberKey {
        &self.root
    }

    /// Every admitted module declaration in deterministic observation order.
    #[must_use]
    pub(crate) fn records(&self) -> &[SourceSetModuleBindingCandidateRecord] {
        &self.records
    }

    /// Number of retained module declarations.
    #[must_use]
    pub(crate) fn len(&self) -> usize {
        self.records.len()
    }
}

/// Prepare an owned module-binding candidate closure from an existing source
/// preparation result.
///
/// Source preparation is handed to the existing restricted source-set
/// handoff.  Any preparation or handoff invariant error is returned before
/// candidate construction, so no partial candidate is exposed.  The digest
/// profile is caller-supplied; this function selects no production profile or
/// dependency policy and does not retain the profile in candidate output.
pub(crate) fn prepare_source_set_module_binding_candidate<'a>(
    prepared: Result<PreparedSourceSet<'a>, SourceSetPreparationError>,
    profile: &DigestProfile<'_>,
) -> Result<SourceSetModuleBindingCandidate, RestrictedSourceSetHandoffError> {
    let handoff = build_restricted_source_set_handoff(prepared)?;
    let observation = observe_source_set_module_binding(&handoff);
    let content = observe_dependency_content(&handoff, profile);

    Ok(join_observations(
        &handoff.root().clone(),
        observation,
        &content,
    ))
}

fn join_observations(
    root: &SourceSetMemberKey,
    observation: SourceSetModuleBindingObservation,
    content: &[DependencyContentObservation],
) -> SourceSetModuleBindingCandidate {
    let records = observation
        .records()
        .iter()
        .cloned()
        .map(|observation| {
            let mut used_content = vec![false; content.len()];
            let dependencies = observation
                .dependencies()
                .iter()
                .map(|dependency| {
                    let content_index = content
                        .iter()
                        .enumerate()
                        .find(|(index, candidate)| {
                            !used_content[*index]
                                && candidate.owner() == dependency.owner()
                                && candidate.declaration() == dependency.dependency()
                        })
                        .map(|(index, _)| index)
                        .expect("module-binding dependency must have content observation");
                    used_content[content_index] = true;
                    SourceSetModuleBindingDependencyEvidence {
                        dependency: dependency.clone(),
                        content: content[content_index].clone(),
                    }
                })
                .collect();
            SourceSetModuleBindingCandidateRecord {
                observation,
                dependencies,
            }
        })
        .collect();

    SourceSetModuleBindingCandidate {
        root: root.clone(),
        records,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::body_document::{Presence, ResourceProfile};
    use crate::dependency_content_observation::DependencyContentOutcome;
    use crate::digest::framed_sha256;
    use crate::restricted_source_set_handoff::RestrictedSourceSetHandoffError;
    use crate::source_set_preparation::{SourceSetInput, SourceSetMemberRole, prepare_source_set};
    use serde_json::Value;
    use std::fmt::Write;

    fn source(document: &str, namespace: &str) -> Vec<u8> {
        let mut value: Value = serde_json::from_slice(include_bytes!(
            "../../../examples/body-documents/stylized-digitigrade-biped.json"
        ))
        .expect("valid fixture");
        value["source"]["document"] = Value::String(document.to_owned());
        value["source"]["namespace"] = Value::String(namespace.to_owned());
        rewrite_namespaces(&mut value["body"], namespace);
        value["source"]["dependencies"] = Value::Array(Vec::new());
        serde_json::to_vec(&value).expect("serializes")
    }

    fn rewrite_namespaces(value: &mut Value, namespace: &str) {
        match value {
            Value::Object(object) => {
                if object.contains_key("namespace") {
                    object.insert("namespace".to_owned(), Value::String(namespace.to_owned()));
                }
                for value in object.values_mut() {
                    rewrite_namespaces(value, namespace);
                }
            }
            Value::Array(values) => {
                for value in values {
                    rewrite_namespaces(value, namespace);
                }
            }
            _ => {}
        }
    }

    fn with_module_locator(source: &[u8], document: &str, namespace: &str) -> Vec<u8> {
        let mut value: Value = serde_json::from_slice(source).expect("source is valid");
        value["body"]["modules"][0]["declaration"]["document"] = document.into();
        value["body"]["modules"][0]["declaration"]["namespace"] = namespace.into();
        serde_json::to_vec(&value).expect("serializes")
    }

    fn with_dependencies(source: &[u8], dependencies: Vec<Value>) -> Vec<u8> {
        let mut value: Value = serde_json::from_slice(source).expect("source is valid");
        value["source"]["dependencies"] = Value::Array(dependencies);
        serde_json::to_vec(&value).expect("serializes")
    }

    fn dependency(document: &str, namespace: &str, digest: String) -> Value {
        serde_json::json!({
            "document": document,
            "namespace": namespace,
            "content_sha256": digest,
        })
    }

    fn digest_text(profile: &DigestProfile<'_>, bytes: &[u8]) -> String {
        let digest = framed_sha256(profile, bytes);
        let mut text = String::from("sha256:");
        for byte in digest.as_bytes() {
            write!(&mut text, "{byte:02x}").expect("writing to String cannot fail");
        }
        text
    }

    fn candidate<'a>(
        root: &'a [u8],
        dependencies: Vec<&'a [u8]>,
        profile: &DigestProfile<'_>,
    ) -> Result<SourceSetModuleBindingCandidate, RestrictedSourceSetHandoffError> {
        prepare_source_set_module_binding_candidate(
            prepare_source_set(SourceSetInput::new(
                root,
                dependencies,
                ResourceProfile::ORDINARY,
            )),
            profile,
        )
    }

    #[test]
    fn matched_dependency_is_joined_with_content_and_provenance() {
        let profile = DigestProfile::new("test-domain", "module-binding").expect("profile");
        let dependency_source = source("dep_doc", "dep_ns");
        let root_source = with_module_locator(&source("root_doc", "root_ns"), "dep_doc", "dep_ns");
        let root_source = with_dependencies(
            &root_source,
            vec![dependency(
                "dep_doc",
                "dep_ns",
                digest_text(&profile, &dependency_source),
            )],
        );

        let candidate = candidate(&root_source, vec![&dependency_source], &profile)
            .expect("candidate succeeds");
        assert_eq!(candidate.root().document(), "root_doc");
        let record = candidate
            .records()
            .iter()
            .find(|record| record.observation().owner().document() == "root_doc")
            .expect("root module record");
        assert_eq!(record.observation().owner_role(), SourceSetMemberRole::Root);
        assert_eq!(record.observation().root_role(), "tail_root");
        assert_eq!(record.observation().presence(), &Presence::Present);
        assert!(!record.observation().optional());
        assert!(record.observation().attachment_required());
        assert_eq!(
            record.observation().instance_root().unwrap().root().role(),
            "tail_root"
        );
        assert_eq!(record.dependencies().len(), 1);
        let dependency = &record.dependencies()[0];
        assert_eq!(
            dependency.dependency().owner_provenance().member(),
            record.observation().owner()
        );
        assert_eq!(dependency.content().owner(), record.observation().owner());
        assert_eq!(
            dependency.content().outcome(),
            DependencyContentOutcome::Matched
        );
        assert_eq!(dependency.content().target().unwrap().document(), "dep_doc");
    }

    #[test]
    fn supplied_dependency_owner_retains_joined_identity_provenance_and_content() {
        let profile = DigestProfile::new("test-domain", "module-binding").expect("profile");
        let leaf_source = source("leaf_doc", "leaf_ns");
        let owner_source = with_dependencies(
            &with_module_locator(&source("owner_doc", "owner_ns"), "leaf_doc", "leaf_ns"),
            vec![dependency(
                "leaf_doc",
                "leaf_ns",
                digest_text(&profile, &leaf_source),
            )],
        );
        let root_source = with_dependencies(
            &with_module_locator(&source("root_doc", "root_ns"), "owner_doc", "owner_ns"),
            vec![dependency(
                "owner_doc",
                "owner_ns",
                digest_text(&profile, &owner_source),
            )],
        );

        let candidate = candidate(&root_source, vec![&owner_source, &leaf_source], &profile)
            .expect("candidate succeeds");
        let record = candidate
            .records()
            .iter()
            .find(|record| record.observation().owner().document() == "owner_doc")
            .expect("supplied dependency module record");
        assert_eq!(
            record.observation().owner_role(),
            SourceSetMemberRole::Dependency
        );
        assert_eq!(
            record.observation().declaration_provenance().member(),
            record.observation().owner()
        );
        assert_eq!(
            record.observation().declaration_provenance().role(),
            SourceSetMemberRole::Dependency
        );
        assert_eq!(
            record.observation().supplied_member().role(),
            Some(SourceSetMemberRole::Dependency)
        );
        assert_eq!(record.dependencies().len(), 1);

        let joined = &record.dependencies()[0];
        assert_eq!(joined.dependency().owner(), record.observation().owner());
        assert_eq!(
            joined.dependency().owner_role(),
            SourceSetMemberRole::Dependency
        );
        assert_eq!(
            joined.dependency().owner_provenance().member(),
            record.observation().owner()
        );
        assert_eq!(
            joined.dependency().owner_provenance().role(),
            SourceSetMemberRole::Dependency
        );
        assert_eq!(joined.content().owner(), record.observation().owner());
        assert_eq!(
            joined.content().owner_role(),
            SourceSetMemberRole::Dependency
        );
        assert_eq!(joined.content().target().unwrap().document(), "leaf_doc");
        assert_eq!(
            joined.content().outcome(),
            DependencyContentOutcome::Matched
        );
    }

    #[test]
    fn missing_and_mismatched_dependency_content_remain_typed_evidence() {
        let profile = DigestProfile::new("test-domain", "module-binding").expect("profile");
        let dependency_source = source("dep_doc", "dep_ns");
        let mut wrong_digest = digest_text(&profile, &dependency_source);
        let replacement = if wrong_digest.as_bytes()[7] == b'0' {
            "1"
        } else {
            "0"
        };
        wrong_digest.replace_range(7..8, replacement);
        let root_source = with_dependencies(
            &with_module_locator(&source("root_doc", "root_ns"), "dep_doc", "dep_ns"),
            vec![dependency("dep_doc", "dep_ns", wrong_digest)],
        );

        let missing = candidate(&root_source, Vec::new(), &profile).expect("candidate succeeds");
        let missing_record = missing
            .records()
            .iter()
            .find(|record| record.observation().owner().document() == "root_doc")
            .expect("root module record");
        assert!(missing_record.observation().supplied_member().is_missing());
        assert_eq!(missing_record.dependencies().len(), 1);
        assert_eq!(
            missing_record.dependencies()[0].content().outcome(),
            DependencyContentOutcome::MissingSuppliedTarget
        );
        assert!(
            missing_record.dependencies()[0]
                .content()
                .target()
                .is_none()
        );

        let mismatched = candidate(&root_source, vec![&dependency_source], &profile)
            .expect("candidate succeeds");
        let mismatched_record = mismatched
            .records()
            .iter()
            .find(|record| record.observation().owner().document() == "root_doc")
            .expect("root module record");
        assert_eq!(
            mismatched_record.observation().supplied_member().role(),
            Some(SourceSetMemberRole::Dependency)
        );
        assert_eq!(mismatched_record.dependencies().len(), 1);
        assert_eq!(
            mismatched_record.dependencies()[0].content().outcome(),
            DependencyContentOutcome::DigestMismatch
        );
        assert!(
            mismatched_record.dependencies()[0]
                .content()
                .computed_digest()
                .is_some()
        );
    }

    #[test]
    fn supplied_locator_can_target_the_designated_root_member() {
        let profile = DigestProfile::new("test-domain", "module-binding").expect("profile");
        let root_source =
            with_module_locator(&source("root_doc", "root_ns"), "root_doc", "root_ns");

        let candidate = candidate(&root_source, Vec::new(), &profile).expect("candidate succeeds");
        let record = candidate
            .records()
            .iter()
            .find(|record| record.observation().owner().document() == "root_doc")
            .expect("root module record");
        assert_eq!(
            record.observation().supplied_member().role(),
            Some(SourceSetMemberRole::Root)
        );
        assert_eq!(
            record
                .observation()
                .supplied_member()
                .structural_root()
                .unwrap()
                .role(),
            "pelvis"
        );
        assert!(record.dependencies().is_empty());
    }

    #[test]
    fn present_attachment_requirement_false_differs_from_absent_root_evidence() {
        let profile = DigestProfile::new("test-domain", "module-binding").expect("profile");
        let mut value: Value = serde_json::from_slice(&source("root_doc", "root_ns")).unwrap();
        value["body"]["modules"][0]["attachment_required"] = false.into();
        value["body"]["attachments"] = Value::Array(Vec::new());
        let present_source = serde_json::to_vec(&value).unwrap();
        let present = candidate(&present_source, Vec::new(), &profile).expect("candidate succeeds");
        let present_record = present
            .records()
            .iter()
            .find(|record| record.observation().owner().document() == "root_doc")
            .expect("present root module record");
        assert_eq!(present_record.observation().presence(), &Presence::Present);
        assert!(!present_record.observation().attachment_required());
        assert!(present_record.observation().instance_root().is_some());

        value["body"]["modules"][0]["presence"] = "absent".into();
        value["body"]["modules"][0]["optional"] = true.into();
        value["body"]["modules"][0]["declaration"]["document"] = "missing_doc".into();
        value["body"]["modules"][0]["declaration"]["namespace"] = "missing_ns".into();
        value["body"]["modules"][0]
            .as_object_mut()
            .unwrap()
            .remove("root");
        value["body"]["attachments"] = Value::Array(Vec::new());
        let root_source = with_dependencies(
            &serde_json::to_vec(&value).unwrap(),
            vec![dependency(
                "missing_doc",
                "missing_ns",
                format!("sha256:{}", "0".repeat(64)),
            )],
        );

        let candidate = candidate(&root_source, Vec::new(), &profile).expect("candidate succeeds");
        let record = candidate
            .records()
            .iter()
            .find(|record| record.observation().owner().document() == "root_doc")
            .expect("root module record");
        assert!(record.observation().supplied_member().is_missing());
        assert_eq!(record.observation().presence(), &Presence::Absent);
        assert!(record.observation().optional());
        assert!(!record.observation().attachment_required());
        assert_eq!(record.observation().root_role(), "tail_root");
        assert!(record.observation().instance_root().is_none());
        assert_eq!(record.dependencies().len(), 1);
        assert_eq!(
            record.dependencies()[0].content().outcome(),
            DependencyContentOutcome::MissingSuppliedTarget
        );
    }

    #[test]
    fn multiple_module_declarations_are_retained_without_selection() {
        let profile = DigestProfile::new("test-domain", "module-binding").expect("profile");
        let dependency_source = source("dep_doc", "dep_ns");
        let mut value: Value = serde_json::from_slice(&with_module_locator(
            &source("root_doc", "root_ns"),
            "dep_doc",
            "dep_ns",
        ))
        .unwrap();
        let mut second = value["body"]["modules"][0].clone();
        second["declaration"]["anchors"] = serde_json::json!(["second"]);
        second["declaration"]["role"] = "second_module".into();
        second["presence"] = "absent".into();
        second["optional"] = true.into();
        second["attachment_required"] = false.into();
        second.as_object_mut().unwrap().remove("root");
        value["body"]["modules"]
            .as_array_mut()
            .unwrap()
            .push(second);
        let root_source = with_dependencies(
            &serde_json::to_vec(&value).unwrap(),
            vec![dependency(
                "dep_doc",
                "dep_ns",
                digest_text(&profile, &dependency_source),
            )],
        );
        let mut reordered_value = value;
        reordered_value["body"]["modules"]
            .as_array_mut()
            .unwrap()
            .reverse();
        let reordered_source = with_dependencies(
            &serde_json::to_vec(&reordered_value).unwrap(),
            vec![dependency(
                "dep_doc",
                "dep_ns",
                digest_text(&profile, &dependency_source),
            )],
        );

        let forward_candidate = candidate(&root_source, vec![&dependency_source], &profile)
            .expect("candidate succeeds");
        let reordered = candidate(&reordered_source, vec![&dependency_source], &profile)
            .expect("reordered candidate succeeds");
        assert_eq!(forward_candidate, reordered);
        let records = forward_candidate
            .records()
            .iter()
            .filter(|record| {
                record.observation().owner().document() == "root_doc"
                    && record.observation().locator().document() == "dep_doc"
            })
            .collect::<Vec<_>>();
        assert_eq!(records.len(), 2);
        assert!(
            records
                .iter()
                .all(|record| record.dependencies().len() == 1)
        );
        assert!(records.iter().all(|record| {
            record.dependencies()[0].content().outcome() == DependencyContentOutcome::Matched
        }));
        assert_ne!(
            records[0].observation().declaration_key(),
            records[1].observation().declaration_key()
        );
        assert!(
            records
                .iter()
                .any(|record| record.observation().presence() == &Presence::Present)
        );
        assert!(
            records
                .iter()
                .any(|record| record.observation().presence() == &Presence::Absent)
        );
    }

    #[test]
    fn joined_dependency_input_reordering_is_deterministic() {
        let profile = DigestProfile::new("test-domain", "module-binding").expect("profile");
        let first_dependency = source("dep_a", "ns_a");
        let second_dependency = source("dep_b", "ns_b");
        let mut root_value: Value = serde_json::from_slice(&with_module_locator(
            &source("root_doc", "root_ns"),
            "dep_a",
            "ns_a",
        ))
        .unwrap();
        let mut second_module = root_value["body"]["modules"][0].clone();
        second_module["declaration"]["document"] = "dep_b".into();
        second_module["declaration"]["namespace"] = "ns_b".into();
        second_module["declaration"]["anchors"] = serde_json::json!(["second"]);
        second_module["declaration"]["role"] = "second_module".into();
        second_module["presence"] = "absent".into();
        second_module["optional"] = true.into();
        second_module["attachment_required"] = false.into();
        second_module.as_object_mut().unwrap().remove("root");
        root_value["body"]["modules"]
            .as_array_mut()
            .unwrap()
            .push(second_module);
        let root_source = with_dependencies(
            &serde_json::to_vec(&root_value).unwrap(),
            vec![
                dependency("dep_a", "ns_a", digest_text(&profile, &first_dependency)),
                dependency("dep_b", "ns_b", digest_text(&profile, &second_dependency)),
            ],
        );
        let first = candidate(
            &root_source,
            vec![&first_dependency, &second_dependency],
            &profile,
        )
        .expect("candidate succeeds");
        let second = candidate(
            &root_source,
            vec![&second_dependency, &first_dependency],
            &profile,
        )
        .expect("candidate succeeds");

        assert_eq!(first, second);
        let joined = first
            .records()
            .iter()
            .filter(|record| record.observation().owner().document() == "root_doc")
            .map(|record| {
                assert_eq!(record.dependencies().len(), 1);
                (
                    record.observation().locator().document(),
                    record.observation().locator().namespace(),
                    record.dependencies()[0].content().outcome(),
                )
            })
            .collect::<Vec<_>>();
        assert_eq!(
            joined,
            vec![
                ("dep_a", "ns_a", DependencyContentOutcome::Matched),
                ("dep_b", "ns_b", DependencyContentOutcome::Matched),
            ]
        );
    }

    #[test]
    fn source_preparation_failure_returns_no_candidate() {
        let profile = DigestProfile::new("test-domain", "module-binding").expect("profile");
        let root_source = source("root_doc", "root_ns");
        let result = candidate(&root_source, vec![b"not-json"], &profile);

        assert!(matches!(
            result,
            Err(RestrictedSourceSetHandoffError::Preparation(_))
        ));
    }
}
