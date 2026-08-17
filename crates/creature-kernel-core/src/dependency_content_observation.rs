//! Crate-private observation of supplied dependency content declarations.
//!
//! This projection verifies only the declared content digest against the exact
//! raw bytes of an already supplied target.  It uses the caller's digest
//! profile and the handoff's existing `(document, namespace)` locator
//! projection.  It does not acquire bytes, resolve dependencies, merge
//! namespaces, normalize JSON, or produce a resolver status or identity.

#![allow(dead_code)]

use crate::body_document::Dependency;
use crate::digest::{DigestProfile, FramedDigest, framed_sha256};
use crate::restricted_source_set_handoff::RestrictedSourceSetHandoff;
use crate::source_set_preparation::{SourceSetMemberKey, SourceSetMemberRole};

/// Content-only outcome for one retained dependency edge.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum DependencyContentOutcome {
    /// The supplied target's exact bytes match the declared digest.
    Matched,
    /// The declaration locator did not name an admitted supplied member.
    MissingSuppliedTarget,
    /// The declaration was not a `sha256:` reference with 64 lowercase hex
    /// characters.  No target hash comparison is performed in this case.
    MalformedDeclaredDigest,
    /// The supplied target was present, but its exact bytes did not match the
    /// well-formed declared digest.
    DigestMismatch,
}

/// One deterministic observation for one currently admitted retained edge.
///
/// `declaration_index` and `declaration_count` retain the observation's
/// position and cardinality in the handoff's stable retained-edge order.
/// They are observation positions, not canonical occurrence identities. The
/// current handoff precondition rejects repeated dependency namespaces; future
/// duplicate support requires owner-defined occurrence/multiplicity semantics
/// before sorting.
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct DependencyContentObservation {
    owner: SourceSetMemberKey,
    owner_role: SourceSetMemberRole,
    declaration_index: usize,
    declaration_count: usize,
    declaration: Dependency,
    target: Option<SourceSetMemberKey>,
    declared_digest: String,
    computed_digest: Option<FramedDigest>,
    outcome: DependencyContentOutcome,
}

impl DependencyContentObservation {
    /// Owning source-set member key.
    #[must_use]
    pub(crate) fn owner(&self) -> &SourceSetMemberKey {
        &self.owner
    }

    /// Root or supplied-dependency role of the owner.
    #[must_use]
    pub(crate) const fn owner_role(&self) -> SourceSetMemberRole {
        self.owner_role
    }

    /// Zero-based position in the deterministic declaration-edge order.
    #[must_use]
    pub(crate) const fn declaration_index(&self) -> usize {
        self.declaration_index
    }

    /// Number of retained dependency edges in the observation.
    #[must_use]
    pub(crate) const fn declaration_count(&self) -> usize {
        self.declaration_count
    }

    /// Complete retained dependency declaration.
    #[must_use]
    pub(crate) fn declaration(&self) -> &Dependency {
        &self.declaration
    }

    /// Supplied target key, when the locator found an admitted member.
    #[must_use]
    pub(crate) fn target(&self) -> Option<&SourceSetMemberKey> {
        self.target.as_ref()
    }

    /// Exact declared digest text.
    #[must_use]
    pub(crate) fn declared_digest(&self) -> &str {
        &self.declared_digest
    }

    /// Computed target digest when a target existed and the declaration was
    /// well formed.  Missing and malformed observations do not hash a target.
    #[must_use]
    pub(crate) const fn computed_digest(&self) -> Option<FramedDigest> {
        self.computed_digest
    }

    /// Content-only outcome.
    #[must_use]
    pub(crate) const fn outcome(&self) -> DependencyContentOutcome {
        self.outcome
    }
}

/// Observe every currently admitted retained dependency edge in stable handoff
/// order, producing exactly one result per retained edge.
///
/// The digest profile is supplied by the caller.  No production profile is
/// selected here.  Target lookup is the handoff's existing structural
/// `(document, namespace)` projection; only exact retained target bytes are
/// hashed.
pub(crate) fn observe_dependency_content(
    handoff: &RestrictedSourceSetHandoff,
    profile: &DigestProfile<'_>,
) -> Vec<DependencyContentObservation> {
    let declaration_count = handoff.dependency_locator_results().len();
    handoff
        .dependency_locator_results()
        .iter()
        .enumerate()
        .map(|(declaration_index, located)| {
            let edge = located.edge();
            let owner = edge.owner().clone();
            let owner_role = handoff
                .members()
                .get(&owner)
                .expect("handoff edge owner is admitted by its construction invariant")
                .role();
            let declaration = edge.dependency().clone();
            let target = located.target().cloned();
            let declared_digest = declaration.content_sha256.clone();

            // Parse before consulting the locator result. A malformed
            // declaration is defensive input to this projection even though
            // current structural admission rejects it upstream; it therefore
            // takes precedence over both missing and supplied targets.
            let parsed_digest = parse_declared_sha256(&declared_digest);
            let (computed_digest, outcome) =
                classify_dependency_content(parsed_digest, target.as_ref(), handoff, profile);

            DependencyContentObservation {
                owner,
                owner_role,
                declaration_index,
                declaration_count,
                declaration,
                target,
                declared_digest,
                computed_digest,
                outcome,
            }
        })
        .collect()
}

fn classify_dependency_content(
    declared_digest: Option<[u8; 32]>,
    target: Option<&SourceSetMemberKey>,
    handoff: &RestrictedSourceSetHandoff,
    profile: &DigestProfile<'_>,
) -> (Option<FramedDigest>, DependencyContentOutcome) {
    let Some(declared_digest) = declared_digest else {
        return (None, DependencyContentOutcome::MalformedDeclaredDigest);
    };
    let Some(target) = target else {
        return (None, DependencyContentOutcome::MissingSuppliedTarget);
    };
    let target_member = handoff
        .members()
        .get(target)
        .expect("located supplied target is admitted by its construction invariant");
    compare_parsed_digest(&declared_digest, target_member.raw_source(), profile)
}

fn compare_parsed_digest(
    declared_digest: &[u8; 32],
    target_bytes: &[u8],
    profile: &DigestProfile<'_>,
) -> (Option<FramedDigest>, DependencyContentOutcome) {
    let computed = framed_sha256(profile, target_bytes);
    let outcome = if computed.as_bytes() == declared_digest {
        DependencyContentOutcome::Matched
    } else {
        DependencyContentOutcome::DigestMismatch
    };
    (Some(computed), outcome)
}

/// Parse the deliberately narrow digest spelling admitted by the source
/// document contract.  Keeping this defensive check local means that a future
/// handoff producer cannot accidentally hash-compare malformed text.
fn parse_declared_sha256(value: &str) -> Option<[u8; 32]> {
    let hex = value.strip_prefix("sha256:")?;
    if hex.len() != 64
        || !hex
            .bytes()
            .all(|byte| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase())
    {
        return None;
    }

    let mut bytes = [0_u8; 32];
    for (index, pair) in hex.as_bytes().chunks_exact(2).enumerate() {
        bytes[index] = (hex_nibble(pair[0])? << 4) | hex_nibble(pair[1])?;
    }
    Some(bytes)
}

fn hex_nibble(byte: u8) -> Option<u8> {
    match byte {
        b'0'..=b'9' => Some(byte - b'0'),
        b'a'..=b'f' => Some(byte - b'a' + 10),
        _ => None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::body_document::ResourceProfile;
    use crate::digest::DigestProfile;
    use crate::restricted_source_set_handoff::build_restricted_source_set_handoff;
    use crate::source_set_preparation::{SourceSetInput, SourceSetMemberRole};
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

    fn declaration(document: &str, namespace: &str, digest: &str) -> Value {
        serde_json::json!({
            "document": document,
            "namespace": namespace,
            "content_sha256": digest,
        })
    }

    fn profile<'a>(domain: &'a str, profile_id: &'a str) -> DigestProfile<'a> {
        DigestProfile::new(domain, profile_id).expect("test profile is valid")
    }

    fn digest_text(profile: &DigestProfile<'_>, bytes: &[u8]) -> String {
        let mut text = String::from("sha256:");
        for byte in framed_sha256(profile, bytes).as_bytes() {
            text.push_str(&format!("{byte:02x}"));
        }
        text
    }

    fn handoff<'a>(root: &'a [u8], dependencies: Vec<&'a [u8]>) -> RestrictedSourceSetHandoff {
        build_restricted_source_set_handoff(crate::source_set_preparation::prepare_source_set(
            SourceSetInput::new(root, dependencies, ResourceProfile::ORDINARY),
        ))
        .expect("source-set handoff succeeds")
    }

    #[test]
    fn matched_digest_hashes_exact_supplied_target_bytes() {
        let profile = profile("test-domain", "profile-a");
        let target = source("dep_doc", "dep_ns");
        let root = with_dependencies(
            &source("root_doc", "root_ns"),
            serde_json::json!([declaration(
                "dep_doc",
                "dep_ns",
                &digest_text(&profile, &target)
            )]),
        );
        let observed = observe_dependency_content(&handoff(&root, vec![&target]), &profile);

        assert_eq!(observed.len(), 1);
        assert_eq!(observed[0].outcome(), DependencyContentOutcome::Matched);
        assert_eq!(observed[0].target().unwrap().namespace(), "dep_ns");
        assert_eq!(
            observed[0].computed_digest(),
            Some(framed_sha256(&profile, &target))
        );
    }

    #[test]
    fn one_byte_target_change_is_a_digest_mismatch() {
        let profile = profile("test-domain", "profile-a");
        let declared_target = source("dep_doc", "dep_ns");
        let mut supplied_target = declared_target.clone();
        supplied_target.push(b' ');
        let root = with_dependencies(
            &source("root_doc", "root_ns"),
            serde_json::json!([declaration(
                "dep_doc",
                "dep_ns",
                &digest_text(&profile, &declared_target)
            )]),
        );
        let observed =
            observe_dependency_content(&handoff(&root, vec![&supplied_target]), &profile);

        assert_eq!(
            observed[0].outcome(),
            DependencyContentOutcome::DigestMismatch
        );
        assert!(observed[0].computed_digest().is_some());
    }

    #[test]
    fn missing_supplied_target_is_not_hashed() {
        let profile = profile("test-domain", "profile-a");
        let root = with_dependencies(
            &source("root_doc", "root_ns"),
            serde_json::json!([declaration(
                "missing_doc",
                "missing_ns",
                "sha256:0000000000000000000000000000000000000000000000000000000000000000"
            )]),
        );
        let observed = observe_dependency_content(&handoff(&root, Vec::new()), &profile);

        assert_eq!(
            observed[0].outcome(),
            DependencyContentOutcome::MissingSuppliedTarget
        );
        assert!(observed[0].target().is_none());
        assert!(observed[0].computed_digest().is_none());
    }

    #[test]
    fn malformed_digest_is_rejected_before_any_hash_comparison() {
        let profile = profile("test-domain", "profile-a");
        for malformed in [
            "sha256:ABC",
            "sha256:not-a-digest",
            "sha512:0000000000000000000000000000000000000000000000000000000000000000",
        ] {
            let (computed, outcome) = classify_dependency_content(
                parse_declared_sha256(malformed),
                None,
                &handoff(&source("root_doc", "root_ns"), Vec::new()),
                &profile,
            );
            assert_eq!(computed, None);
            assert_eq!(outcome, DependencyContentOutcome::MalformedDeclaredDigest);
        }
        // Admission currently rejects malformed declarations before a handoff
        // can exist. This exercises the defensive malformed-plus-no-target
        // branch without weakening that upstream structural contract.
    }

    #[test]
    fn admitted_edges_retain_one_observation_each() {
        let profile = profile("test-domain", "profile-a");
        let target_a = source("dep_a", "a_ns");
        let target_b = source("dep_b", "b_ns");
        let root = with_dependencies(
            &source("root_doc", "root_ns"),
            serde_json::json!([
                declaration("dep_a", "a_ns", &digest_text(&profile, &target_a)),
                declaration("dep_b", "b_ns", &digest_text(&profile, &target_b)),
            ]),
        );
        let observed =
            observe_dependency_content(&handoff(&root, vec![&target_a, &target_b]), &profile);

        assert_eq!(observed.len(), 2);
        assert_eq!(observed[0].declaration_index(), 0);
        assert_eq!(observed[1].declaration_index(), 1);
        assert_eq!(observed[0].declaration_count(), 2);
        assert_eq!(observed[1].declaration_count(), 2);
        assert_ne!(observed[0].target(), observed[1].target());

        // Exact duplicate declarations are intentionally not tested here:
        // current structural admission rejects repeated dependency namespaces
        // before a handoff is built. The observation consumes the retained
        // edge vector directly and introduces no additional deduplication.
    }

    #[test]
    fn supplied_member_reordering_does_not_change_output() {
        let profile = profile("test-domain", "profile-a");
        let target_a = source("dep_a", "a_ns");
        let target_b = source("dep_b", "b_ns");
        let root = with_dependencies(
            &source("root_doc", "root_ns"),
            serde_json::json!([
                declaration("dep_a", "a_ns", &digest_text(&profile, &target_a)),
                declaration("dep_b", "b_ns", &digest_text(&profile, &target_b)),
            ]),
        );
        let first =
            observe_dependency_content(&handoff(&root, vec![&target_a, &target_b]), &profile);
        let second =
            observe_dependency_content(&handoff(&root, vec![&target_b, &target_a]), &profile);
        assert_eq!(first, second);
    }

    #[test]
    fn root_and_nested_owner_roles_follow_stable_edge_order() {
        let profile = profile("test-domain", "profile-a");
        let leaf = source("leaf_doc", "b_ns");
        let dependency_base = source("dep_doc", "a_ns");
        let dependency = with_dependencies(
            &dependency_base,
            serde_json::json!([declaration(
                "leaf_doc",
                "b_ns",
                &digest_text(&profile, &leaf)
            )]),
        );
        let root = with_dependencies(
            &source("root_doc", "root_ns"),
            serde_json::json!([declaration(
                "dep_doc",
                "a_ns",
                &digest_text(&profile, &dependency)
            )]),
        );
        let observed =
            observe_dependency_content(&handoff(&root, vec![&dependency, &leaf]), &profile);

        assert_eq!(observed.len(), 2);
        assert_eq!(observed[0].owner().document(), "root_doc");
        assert_eq!(observed[0].owner_role(), SourceSetMemberRole::Root);
        assert_eq!(observed[1].owner().document(), "dep_doc");
        assert_eq!(observed[1].owner_role(), SourceSetMemberRole::Dependency);
    }

    #[test]
    fn changing_caller_profile_changes_digest_but_not_structural_match() {
        let first_profile = profile("test-domain", "profile-a");
        let second_profile = profile("other-domain", "profile-b");
        let target = source("dep_doc", "dep_ns");
        let root = with_dependencies(
            &source("root_doc", "root_ns"),
            serde_json::json!([declaration(
                "dep_doc",
                "dep_ns",
                &digest_text(&second_profile, &target)
            )]),
        );
        let first = observe_dependency_content(&handoff(&root, vec![&target]), &first_profile);
        let second = observe_dependency_content(&handoff(&root, vec![&target]), &second_profile);

        assert_eq!(first[0].outcome(), DependencyContentOutcome::DigestMismatch);
        assert_eq!(second[0].outcome(), DependencyContentOutcome::Matched);
        assert_ne!(first[0].computed_digest(), second[0].computed_digest());
        assert_eq!(first[0].target(), second[0].target());
    }
}
