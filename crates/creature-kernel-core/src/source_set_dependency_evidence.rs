//! Crate-private deterministic evidence for source-set dependency topology.
//!
//! This reducer consumes the already-built provenance/topology observation and
//! only makes its missing-target, cycle-back-edge, and unreachable-member
//! evidence convenient to inspect.  It does not resolve or select a
//! dependency, verify content, mutate source, assign status, or activate R3.

#![allow(dead_code)]

use crate::source_set_preparation::{SourceSetMemberKey, SourceSetMemberRole};
use crate::source_set_provenance_observation::{
    SourceSetDependencyEdgeObservation, SourceSetProvenanceObservation,
};
use std::cmp::Ordering;

/// One deterministic source-set dependency-topology finding.
///
/// The first two variants retain the complete declaration occurrence rather
/// than reducing declarations to a set.  Consequently two equal declarations
/// remain two findings when the source-set observation contains both.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum SourceSetDependencyTopologyFinding {
    /// A declaration locator did not name a supplied source-set member.
    MissingSuppliedTarget {
        /// Member that declared the dependency.
        declaring_member: SourceSetMemberKey,
        /// Root/dependency role of the declaring member.
        declaring_role: SourceSetMemberRole,
        /// Complete retained declaration occurrence and provenance.
        declaration: SourceSetDependencyEdgeObservation,
        /// Locator key named by the declaration.
        target: SourceSetMemberKey,
    },
    /// A reachable declaration points to a member active on the DFS stack.
    DependencyCycleBackEdge {
        /// Member that declared the back-edge.
        declaring_member: SourceSetMemberKey,
        /// Root/dependency role of the declaring member.
        declaring_role: SourceSetMemberRole,
        /// Complete retained declaration occurrence and provenance.
        declaration: SourceSetDependencyEdgeObservation,
        /// Supplied member reached by the back-edge.
        target: SourceSetMemberKey,
    },
    /// A supplied member was not reached from the designated root.
    SuppliedMemberUnreachable {
        /// Unreached supplied member key.
        member: SourceSetMemberKey,
        /// Root/dependency role retained by the provenance inventory.
        role: SourceSetMemberRole,
    },
}

/// Deterministic topology evidence in fixed finding-class order.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct SourceSetDependencyTopologyEvidence {
    findings: Vec<SourceSetDependencyTopologyFinding>,
}

impl SourceSetDependencyTopologyEvidence {
    /// Every finding in fixed class/member/edge order.
    #[must_use]
    pub(crate) fn findings(&self) -> &[SourceSetDependencyTopologyFinding] {
        &self.findings
    }

    /// Number of retained findings.
    #[must_use]
    pub(crate) fn len(&self) -> usize {
        self.findings.len()
    }

    /// Whether no topology findings were retained.
    #[must_use]
    pub(crate) fn is_empty(&self) -> bool {
        self.findings.is_empty()
    }
}

/// Reduce an existing provenance observation to topology evidence.
///
/// Missing declarations are retained even when their declaring member is
/// unreachable.  Back-edges and unreachable members are emitted separately;
/// neither is collapsed into status, validity, or a selected dependency.
#[must_use]
pub(crate) fn collect_source_set_dependency_evidence(
    observation: &SourceSetProvenanceObservation,
) -> SourceSetDependencyTopologyEvidence {
    let mut findings = Vec::new();

    let mut missing = observation
        .all_missing_supplied_targets()
        .iter()
        .map(|declaration| {
            assert_declaring_member_is_consistent(observation, declaration);
            let target = declaration.target();
            assert!(
                !observation.members().contains_key(&target),
                "missing dependency evidence names a supplied member: {target}"
            );
            SourceSetDependencyTopologyFinding::MissingSuppliedTarget {
                declaring_member: declaration.owner().clone(),
                declaring_role: declaration.owner_role(),
                declaration: declaration.clone(),
                target,
            }
        })
        .collect::<Vec<_>>();
    missing.sort_by(cmp_declaration_finding);
    findings.extend(missing);

    let mut cycles = observation
        .back_edges()
        .iter()
        .map(|back_edge| {
            let declaration = back_edge.declaration().clone();
            assert_declaring_member_is_consistent(observation, &declaration);
            let target = back_edge.target();
            observation
                .members()
                .get(&target)
                .expect("cycle back-edge target missing from supplied-member index");
            assert_eq!(
                back_edge.supplied_target(),
                Some(&target),
                "cycle back-edge supplied target disagrees with locator target"
            );
            SourceSetDependencyTopologyFinding::DependencyCycleBackEdge {
                declaring_member: declaration.owner().clone(),
                declaring_role: declaration.owner_role(),
                declaration,
                target,
            }
        })
        .collect::<Vec<_>>();
    cycles.sort_by(cmp_declaration_finding);
    findings.extend(cycles);

    for member in observation.unreachable_members() {
        let inventory = observation
            .members()
            .get(member)
            .expect("unreachable member missing from provenance member index");
        assert_eq!(
            inventory.key(),
            member,
            "provenance member index returned an inventory under the wrong key"
        );
        findings.push(
            SourceSetDependencyTopologyFinding::SuppliedMemberUnreachable {
                member: member.clone(),
                role: inventory.role(),
            },
        );
    }

    SourceSetDependencyTopologyEvidence { findings }
}

fn assert_declaring_member_is_consistent(
    observation: &SourceSetProvenanceObservation,
    declaration: &SourceSetDependencyEdgeObservation,
) {
    let inventory = observation
        .members()
        .get(declaration.owner())
        .expect("dependency declaration owner missing from provenance member index");
    assert_eq!(
        inventory.key(),
        declaration.owner(),
        "provenance member index returned an inventory under the wrong owner key"
    );
    assert_eq!(
        inventory.role(),
        declaration.owner_role(),
        "dependency declaration role disagrees with its provenance inventory"
    );
}

fn cmp_declaration_finding(
    left: &SourceSetDependencyTopologyFinding,
    right: &SourceSetDependencyTopologyFinding,
) -> Ordering {
    let left_declaration = declaration_from_finding(left);
    let right_declaration = declaration_from_finding(right);
    left_declaration
        .edge()
        .cmp(right_declaration.edge())
        .then_with(|| {
            left_declaration
                .owner_role()
                .cmp(&right_declaration.owner_role())
        })
        .then_with(|| left_declaration.target().cmp(&right_declaration.target()))
}

fn declaration_from_finding(
    finding: &SourceSetDependencyTopologyFinding,
) -> &SourceSetDependencyEdgeObservation {
    match finding {
        SourceSetDependencyTopologyFinding::MissingSuppliedTarget { declaration, .. }
        | SourceSetDependencyTopologyFinding::DependencyCycleBackEdge { declaration, .. } => {
            declaration
        }
        SourceSetDependencyTopologyFinding::SuppliedMemberUnreachable { .. } => {
            unreachable!("unreachable-member findings have no declaration edge")
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::body_document::ResourceProfile;
    use crate::restricted_source_set_handoff::build_restricted_source_set_handoff;
    use crate::source_set_preparation::{SourceSetInput, prepare_source_set};
    use crate::source_set_provenance_observation::observe_source_set_provenance;
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

    fn observation(root: &[u8], dependencies: Vec<&[u8]>) -> SourceSetProvenanceObservation {
        let handoff = build_restricted_source_set_handoff(prepare_source_set(SourceSetInput::new(
            root,
            dependencies,
            ResourceProfile::ORDINARY,
        )))
        .expect("source-set handoff succeeds");
        observe_source_set_provenance(&handoff)
    }

    #[test]
    fn clean_topology_has_no_findings() {
        let root = with_dependencies(
            &source("root_doc", "root_ns"),
            serde_json::json!([declaration("dep_doc", "dep_ns", 'a')]),
        );
        let dep = source("dep_doc", "dep_ns");
        let evidence = collect_source_set_dependency_evidence(&observation(&root, vec![&dep]));
        assert!(evidence.is_empty());
    }

    #[test]
    fn missing_target_retains_declaration_and_context() {
        let root = with_dependencies(
            &source("root_doc", "root_ns"),
            serde_json::json!([declaration("missing_doc", "missing_ns", 'a')]),
        );
        let evidence = collect_source_set_dependency_evidence(&observation(&root, Vec::new()));
        assert_eq!(evidence.len(), 1);
        let SourceSetDependencyTopologyFinding::MissingSuppliedTarget {
            declaring_member,
            declaring_role,
            declaration,
            target,
        } = &evidence.findings()[0]
        else {
            panic!("expected missing-target finding");
        };
        assert_eq!(declaring_member.document(), "root_doc");
        assert_eq!(*declaring_role, SourceSetMemberRole::Root);
        assert_eq!(declaration.owner(), declaring_member);
        assert_eq!(declaration.owner_role(), *declaring_role);
        assert_eq!(declaration.target(), target.clone());
        assert_eq!(target.document(), "missing_doc");
        assert_eq!(
            declaration.dependency().content_sha256,
            "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        );
    }

    #[test]
    fn reachable_cycle_emits_back_edge() {
        let root = with_dependencies(
            &source("root_doc", "root_ns"),
            serde_json::json!([declaration("dep_doc", "dep_ns", 'a')]),
        );
        let dep = with_dependencies(
            &source("dep_doc", "dep_ns"),
            serde_json::json!([declaration("root_doc", "root_ns", 'b')]),
        );
        let evidence = collect_source_set_dependency_evidence(&observation(&root, vec![&dep]));
        assert_eq!(evidence.len(), 1);
        let SourceSetDependencyTopologyFinding::DependencyCycleBackEdge { target, .. } =
            &evidence.findings()[0]
        else {
            panic!("expected cycle finding");
        };
        assert_eq!(target.document(), "root_doc");
        assert_eq!(target.namespace(), "root_ns");
    }

    #[test]
    fn unreachable_member_and_its_missing_declaration_are_both_retained() {
        let root = with_dependencies(
            &source("root_doc", "root_ns"),
            serde_json::json!([declaration("reachable_doc", "reachable_ns", 'a')]),
        );
        let reachable = source("reachable_doc", "reachable_ns");
        let unreachable = with_dependencies(
            &source("unreachable_doc", "unreachable_ns"),
            serde_json::json!([declaration("missing_doc", "missing_ns", 'b')]),
        );
        let evidence = collect_source_set_dependency_evidence(&observation(
            &root,
            vec![&unreachable, &reachable],
        ));
        assert_eq!(evidence.len(), 2);
        assert!(matches!(
            &evidence.findings()[0],
            SourceSetDependencyTopologyFinding::MissingSuppliedTarget { declaring_member, .. }
                if declaring_member.document() == "unreachable_doc"
        ));
        assert!(matches!(
            &evidence.findings()[1],
            SourceSetDependencyTopologyFinding::SuppliedMemberUnreachable { member, role }
                if member.document() == "unreachable_doc"
                    && *role == SourceSetMemberRole::Dependency
        ));
    }

    #[test]
    fn duplicate_declarations_remain_distinct_and_order_is_canonical() {
        let root_first = with_dependencies(
            &source("root_doc", "root_ns"),
            serde_json::json!([
                declaration("owner_b", "owner_b_ns", 'b'),
                declaration("owner_a", "owner_a_ns", 'a')
            ]),
        );
        let root_second = with_dependencies(
            &source("root_doc", "root_ns"),
            serde_json::json!([
                declaration("owner_a", "owner_a_ns", 'a'),
                declaration("owner_b", "owner_b_ns", 'b')
            ]),
        );
        let owner_a = with_dependencies(
            &source("owner_a", "owner_a_ns"),
            serde_json::json!([declaration("missing_doc", "missing_ns", 'a')]),
        );
        let owner_b = with_dependencies(
            &source("owner_b", "owner_b_ns"),
            serde_json::json!([declaration("missing_doc", "missing_ns", 'a')]),
        );
        let first = collect_source_set_dependency_evidence(&observation(
            &root_first,
            vec![&owner_b, &owner_a],
        ));
        let second = collect_source_set_dependency_evidence(&observation(
            &root_second,
            vec![&owner_a, &owner_b],
        ));
        assert_eq!(first, second);
        assert_eq!(first.len(), 2);
        assert_eq!(
            first
                .findings()
                .iter()
                .filter_map(|finding| match finding {
                    SourceSetDependencyTopologyFinding::MissingSuppliedTarget {
                        target, ..
                    } => {
                        Some((target.document(), finding_declaring_document(finding)))
                    }
                    _ => None,
                })
                .collect::<Vec<_>>(),
            vec![("missing_doc", "owner_a"), ("missing_doc", "owner_b")]
        );
    }

    fn finding_declaring_document(finding: &SourceSetDependencyTopologyFinding) -> &str {
        match finding {
            SourceSetDependencyTopologyFinding::MissingSuppliedTarget {
                declaring_member, ..
            }
            | SourceSetDependencyTopologyFinding::DependencyCycleBackEdge {
                declaring_member,
                ..
            } => declaring_member.document(),
            SourceSetDependencyTopologyFinding::SuppliedMemberUnreachable { .. } => {
                panic!("unexpected unreachable finding")
            }
        }
    }
}
