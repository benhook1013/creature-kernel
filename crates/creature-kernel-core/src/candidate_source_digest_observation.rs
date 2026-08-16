//! Crate-private observation of exact source bytes for an admitted source set.
//!
//! This projection computes one caller-profiled framed digest per retained
//! source-set member.  It is deliberately only an observation: it does not
//! verify dependency declarations, derive canonical identity, normalize
//! source, or combine member digests into a source-set digest.

#![allow(dead_code)]

use crate::digest::{DigestProfile, FramedDigest, framed_sha256};
use crate::restricted_source_set_handoff::RestrictedSourceSetHandoff;
use crate::source_set_preparation::{SourceSetMemberKey, SourceSetMemberRole};
use std::collections::BTreeMap;

/// One member's exact-byte digest observation and retained source-set role.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct CandidateSourceDigestMemberObservation {
    role: SourceSetMemberRole,
    digest: FramedDigest,
}

impl CandidateSourceDigestMemberObservation {
    /// Root or supplied-dependency role retained from the handoff.
    #[must_use]
    pub(crate) const fn role(&self) -> SourceSetMemberRole {
        self.role
    }

    /// Framed digest of this member's exact retained raw source bytes.
    #[must_use]
    pub(crate) const fn digest(&self) -> FramedDigest {
        self.digest
    }
}

/// Deterministically keyed per-member candidate digest observations.
///
/// The root key and member keys are copied from the owned handoff.  Each
/// digest is computed over exactly one member's retained [`raw_source`]
/// bytes.  The declared dependency `content_sha256` text is not consulted.
/// This type is not a canonical identity, dependency verification result, or
/// aggregate source-set digest.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct CandidateSourceDigestObservation {
    root: SourceSetMemberKey,
    members: BTreeMap<SourceSetMemberKey, CandidateSourceDigestMemberObservation>,
}

impl CandidateSourceDigestObservation {
    /// Root member key retained from the handoff.
    #[must_use]
    pub(crate) fn root(&self) -> &SourceSetMemberKey {
        &self.root
    }

    /// Deterministically keyed member observations.
    #[must_use]
    pub(crate) fn members(
        &self,
    ) -> &BTreeMap<SourceSetMemberKey, CandidateSourceDigestMemberObservation> {
        &self.members
    }
}

/// Observe one framed digest for each retained source-set member.
///
/// `profile` is supplied by the caller and is already validated by
/// [`DigestProfile::new`].  This function only reads the owned handoff and
/// therefore cannot be affected by mutation of the input storage that
/// preceded handoff construction.
pub(crate) fn observe_candidate_source_digests(
    handoff: &RestrictedSourceSetHandoff,
    profile: &DigestProfile<'_>,
) -> CandidateSourceDigestObservation {
    let members = handoff
        .members()
        .iter()
        .map(|(key, member)| {
            (
                key.clone(),
                CandidateSourceDigestMemberObservation {
                    role: member.role(),
                    digest: framed_sha256(profile, member.raw_source()),
                },
            )
        })
        .collect();

    CandidateSourceDigestObservation {
        root: handoff.root().clone(),
        members,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::body_document::ResourceProfile;
    use crate::restricted_source_set_handoff::build_restricted_source_set_handoff;
    use crate::source_set_preparation::{SourceSetInput, SourceSetMemberRole};
    use serde_json::Value;

    fn source(document: &str, namespace: &str, pretty: bool) -> Vec<u8> {
        let mut value: Value = serde_json::from_slice(include_bytes!(
            "../../../examples/body-documents/stylized-digitigrade-biped.json"
        ))
        .expect("example source is valid JSON");
        value["source"]["document"] = Value::String(document.to_owned());
        value["source"]["namespace"] = Value::String(namespace.to_owned());
        rewrite_namespaces(&mut value["body"], namespace);
        value["source"]["dependencies"] = Value::Array(Vec::new());
        if pretty {
            serde_json::to_vec_pretty(&value).expect("source serializes")
        } else {
            serde_json::to_vec(&value).expect("source serializes")
        }
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
        .expect("handoff succeeds")
    }

    fn profile<'a>(domain: &'a str, profile_id: &'a str) -> DigestProfile<'a> {
        DigestProfile::new(domain, profile_id).expect("test profile is valid")
    }

    #[test]
    fn root_and_two_dependencies_preserve_cardinality_roles_and_key_order() {
        let root = source("root_doc", "root_ns", false);
        let first_dependency = source("dep_a", "a_ns", false);
        let second_dependency = source("dep_b", "b_ns", false);
        let handoff = handoff(&root, vec![&first_dependency, &second_dependency]);

        let observed = observe_candidate_source_digests(&handoff, &profile("domain", "profile"));

        assert_eq!(observed.root(), handoff.root());
        assert_eq!(observed.members().len(), 3);
        let keys = observed
            .members()
            .keys()
            .map(|key| (key.document(), key.namespace()))
            .collect::<Vec<_>>();
        assert_eq!(
            keys,
            vec![
                ("dep_a", "a_ns"),
                ("dep_b", "b_ns"),
                ("root_doc", "root_ns")
            ]
        );
        assert_eq!(
            observed.members()[handoff.root()].role(),
            SourceSetMemberRole::Root
        );
        assert_eq!(
            observed
                .members()
                .values()
                .filter(|member| member.role() == SourceSetMemberRole::Dependency)
                .count(),
            2
        );
    }

    #[test]
    fn reversed_supplied_member_order_gives_identical_observations() {
        let root = source("root_doc", "root_ns", false);
        let first_dependency = source("dep_a", "a_ns", false);
        let second_dependency = source("dep_b", "b_ns", false);
        let first = handoff(&root, vec![&first_dependency, &second_dependency]);
        let second = handoff(&root, vec![&second_dependency, &first_dependency]);
        let profile = profile("domain", "profile");

        assert_eq!(
            observe_candidate_source_digests(&first, &profile),
            observe_candidate_source_digests(&second, &profile)
        );
    }

    #[test]
    fn domain_and_profile_changes_change_each_member_digest() {
        let root = source("root_doc", "root_ns", false);
        let dependency = source("dep_doc", "dep_ns", false);
        let handoff = handoff(&root, vec![&dependency]);
        let base = observe_candidate_source_digests(&handoff, &profile("domain", "profile"));
        let other_domain =
            observe_candidate_source_digests(&handoff, &profile("other-domain", "profile"));
        let other_profile =
            observe_candidate_source_digests(&handoff, &profile("domain", "other-profile"));

        for key in handoff.members().keys() {
            assert_ne!(
                base.members()[key].digest(),
                other_domain.members()[key].digest()
            );
            assert_ne!(
                base.members()[key].digest(),
                other_profile.members()[key].digest()
            );
        }
    }

    #[test]
    fn exact_formatting_change_changes_only_that_member_digest() {
        let compact_root = source("root_doc", "root_ns", false);
        let formatted_root = source("root_doc", "root_ns", true);
        let dependency = source("dep_doc", "dep_ns", false);
        let compact_handoff = handoff(&compact_root, vec![&dependency]);
        let formatted_handoff = handoff(&formatted_root, vec![&dependency]);
        let profile = profile("domain", "profile");
        let compact = observe_candidate_source_digests(&compact_handoff, &profile);
        let formatted = observe_candidate_source_digests(&formatted_handoff, &profile);

        assert_eq!(compact.root(), formatted.root());
        assert_eq!(compact.members().len(), formatted.members().len());
        assert_ne!(
            compact.members()[compact.root()].digest(),
            formatted.members()[formatted.root()].digest()
        );
        let dependency_key = compact
            .members()
            .iter()
            .find_map(|(key, member)| {
                (member.role() == SourceSetMemberRole::Dependency).then_some(key)
            })
            .expect("dependency exists");
        assert_eq!(
            compact.members()[dependency_key].digest(),
            formatted.members()[dependency_key].digest()
        );
    }

    #[test]
    fn wrong_but_schema_valid_declared_hash_does_not_fail_or_affect_observation() {
        let root = with_dependencies(
            &source("root_doc", "root_ns", false),
            serde_json::json!([declaration("dep_doc", "dep_ns", 'f')]),
        );
        let dependency = source("dep_doc", "dep_ns", false);
        let handoff = handoff(&root, vec![&dependency]);
        let profile = profile("domain", "profile");
        let observed = observe_candidate_source_digests(&handoff, &profile);

        assert_eq!(observed.members().len(), 2);
        for (key, member) in handoff.members() {
            assert_eq!(
                observed.members()[key].digest(),
                framed_sha256(&profile, member.raw_source())
            );
        }
    }

    #[test]
    fn input_storage_mutation_cannot_change_owned_observation() {
        let mut root = source("root_doc", "root_ns", false);
        let mut dependency = source("dep_doc", "dep_ns", false);
        let handoff = handoff(&root, vec![&dependency]);
        let profile = profile("domain", "profile");
        let before = observe_candidate_source_digests(&handoff, &profile);
        root.fill(b'x');
        dependency.fill(b'y');
        let after = observe_candidate_source_digests(&handoff, &profile);

        assert_eq!(before, after);
    }
}
