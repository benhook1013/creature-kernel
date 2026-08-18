//! Crate-private observation of module-binding ingredients.

#![allow(dead_code)]

use crate::body_document::{Containment, Module, Presence};
use crate::body_graph::ModuleDeclarationKey;
use crate::restricted_source_set_handoff::RestrictedSourceSetHandoff;
use crate::semantic_address::AddressKey;
use crate::source_set_preparation::{
    SourceSetDependencyEdge, SourceSetMemberKey, SourceSetMemberRole,
};
use crate::source_set_provenance_observation::{
    SourceSetRecordProvenance, observe_source_set_provenance,
};

/// Document and namespace named by a module declaration.
#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub(crate) struct SourceSetModuleBindingLocator {
    document: String,
    namespace: String,
}

impl SourceSetModuleBindingLocator {
    #[must_use]
    pub(crate) fn document(&self) -> &str {
        &self.document
    }

    #[must_use]
    pub(crate) fn namespace(&self) -> &str {
        &self.namespace
    }
}

/// Evidence that a module locator names no admitted member or one admitted
/// member.  This is a member-table lookup only; it does not select or verify
/// a dependency.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum SourceSetModuleBindingSuppliedMember {
    Missing {
        target: SourceSetModuleBindingLocator,
    },
    Supplied {
        member: SourceSetMemberKey,
        role: SourceSetMemberRole,
        structural_root: AddressKey,
    },
}

impl SourceSetModuleBindingSuppliedMember {
    #[must_use]
    pub(crate) const fn is_missing(&self) -> bool {
        matches!(self, Self::Missing { .. })
    }

    #[must_use]
    pub(crate) fn member(&self) -> Option<&SourceSetMemberKey> {
        match self {
            Self::Missing { .. } => None,
            Self::Supplied { member, .. } => Some(member),
        }
    }

    #[must_use]
    pub(crate) const fn role(&self) -> Option<SourceSetMemberRole> {
        match self {
            Self::Missing { .. } => None,
            Self::Supplied { role, .. } => Some(*role),
        }
    }

    #[must_use]
    pub(crate) fn structural_root(&self) -> Option<&AddressKey> {
        match self {
            Self::Missing { .. } => None,
            Self::Supplied {
                structural_root, ..
            } => Some(structural_root),
        }
    }
}

/// One owner-authored dependency declaration matching a module locator.
///
/// The edge is retained verbatim, including opaque hash/revision text.  The
/// existing provenance observation is retained as shared owner/member-role
/// evidence for the occurrence. Matching edges are retained without another
/// set-deduplication step, although current structural admission permits at
/// most one dependency declaration per namespace. The complete declaration
/// occurrence is the retained edge.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct SourceSetModuleBindingDependency {
    edge: SourceSetDependencyEdge,
    owner_role: SourceSetMemberRole,
    owner_provenance: SourceSetRecordProvenance,
}

impl SourceSetModuleBindingDependency {
    #[must_use]
    pub(crate) fn edge(&self) -> &SourceSetDependencyEdge {
        &self.edge
    }

    #[must_use]
    pub(crate) fn owner_provenance(&self) -> &SourceSetRecordProvenance {
        &self.owner_provenance
    }

    #[must_use]
    pub(crate) fn owner(&self) -> &SourceSetMemberKey {
        self.edge.owner()
    }

    #[must_use]
    pub(crate) const fn owner_role(&self) -> SourceSetMemberRole {
        self.owner_role
    }

    #[must_use]
    pub(crate) fn dependency(&self) -> &crate::body_document::Dependency {
        self.edge.dependency()
    }
}

/// Present module instance root and its immediate owner-local containment
/// parent.  Absent modules carry no value of this type.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct SourceSetModuleInstanceRoot {
    root: AddressKey,
    parent: Option<AddressKey>,
}

impl SourceSetModuleInstanceRoot {
    #[must_use]
    pub(crate) fn root(&self) -> &AddressKey {
        &self.root
    }

    #[must_use]
    pub(crate) fn parent(&self) -> Option<&AddressKey> {
        self.parent.as_ref()
    }
}

/// One deterministic module-binding observation record.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct SourceSetModuleBindingRecord {
    owner: SourceSetMemberKey,
    owner_role: SourceSetMemberRole,
    declaration_key: ModuleDeclarationKey,
    module: String,
    root_role: String,
    instance_anchor: String,
    presence: Presence,
    optional: bool,
    attachment_required: bool,
    declaration_provenance: SourceSetRecordProvenance,
    locator: SourceSetModuleBindingLocator,
    dependencies: Vec<SourceSetModuleBindingDependency>,
    supplied_member: SourceSetModuleBindingSuppliedMember,
    instance_root: Option<SourceSetModuleInstanceRoot>,
}

impl SourceSetModuleBindingRecord {
    #[must_use]
    pub(crate) fn owner(&self) -> &SourceSetMemberKey {
        &self.owner
    }

    #[must_use]
    pub(crate) const fn owner_role(&self) -> SourceSetMemberRole {
        self.owner_role
    }

    #[must_use]
    pub(crate) fn declaration_key(&self) -> &ModuleDeclarationKey {
        &self.declaration_key
    }

    #[must_use]
    pub(crate) fn module(&self) -> &str {
        &self.module
    }

    #[must_use]
    pub(crate) fn root_role(&self) -> &str {
        &self.root_role
    }

    #[must_use]
    pub(crate) fn instance_anchor(&self) -> &str {
        &self.instance_anchor
    }

    #[must_use]
    pub(crate) const fn presence(&self) -> &Presence {
        &self.presence
    }

    #[must_use]
    pub(crate) const fn optional(&self) -> bool {
        self.optional
    }

    #[must_use]
    pub(crate) const fn attachment_required(&self) -> bool {
        self.attachment_required
    }

    #[must_use]
    pub(crate) fn declaration_provenance(&self) -> &SourceSetRecordProvenance {
        &self.declaration_provenance
    }

    #[must_use]
    pub(crate) fn locator(&self) -> &SourceSetModuleBindingLocator {
        &self.locator
    }

    #[must_use]
    pub(crate) fn dependencies(&self) -> &[SourceSetModuleBindingDependency] {
        &self.dependencies
    }

    #[must_use]
    pub(crate) fn supplied_member(&self) -> &SourceSetModuleBindingSuppliedMember {
        &self.supplied_member
    }

    #[must_use]
    pub(crate) fn instance_root(&self) -> Option<&SourceSetModuleInstanceRoot> {
        self.instance_root.as_ref()
    }
}

/// Deterministic owned module-binding ingredient records.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct SourceSetModuleBindingObservation {
    records: Vec<SourceSetModuleBindingRecord>,
}

impl SourceSetModuleBindingObservation {
    #[must_use]
    pub(crate) fn records(&self) -> &[SourceSetModuleBindingRecord] {
        &self.records
    }

    #[must_use]
    pub(crate) fn len(&self) -> usize {
        self.records.len()
    }
}

/// Observe one record for each admitted module declaration.
#[must_use]
pub(crate) fn observe_source_set_module_binding(
    handoff: &RestrictedSourceSetHandoff,
) -> SourceSetModuleBindingObservation {
    let provenance = observe_source_set_provenance(handoff);
    let mut records = Vec::new();

    for (owner, member) in handoff.members() {
        let graph = member.prepared_source().graph();
        for (declaration_key, module) in graph.modules() {
            let locator = SourceSetModuleBindingLocator {
                document: module.declaration.document.clone(),
                namespace: module.declaration.namespace.clone(),
            };
            let declaration_provenance = provenance
                .members()
                .get(owner)
                .and_then(|member| member.module_declarations().get(declaration_key))
                .expect("admitted module must have provenance")
                .clone();
            let dependencies = provenance
                .declared_dependency_edges()
                .iter()
                .filter(|edge| {
                    edge.owner() == owner
                        && edge.dependency().document == locator.document
                        && edge.dependency().namespace == locator.namespace
                })
                .map(|edge| SourceSetModuleBindingDependency {
                    edge: edge.edge().clone(),
                    owner_role: edge.owner_role(),
                    owner_provenance: declaration_provenance.clone(),
                })
                .collect();

            records.push(SourceSetModuleBindingRecord {
                owner: owner.clone(),
                owner_role: member.role(),
                declaration_key: declaration_key.clone(),
                module: module.module.clone(),
                root_role: module.root_role.clone(),
                instance_anchor: module.instance_anchor.clone(),
                presence: module.presence.clone(),
                optional: module.optional,
                attachment_required: module.attachment_required,
                declaration_provenance,
                locator: locator.clone(),
                dependencies,
                supplied_member: supplied_member_evidence(handoff, &locator),
                instance_root: instance_root_evidence(graph, module),
            });
        }
    }

    SourceSetModuleBindingObservation { records }
}

fn supplied_member_evidence(
    handoff: &RestrictedSourceSetHandoff,
    locator: &SourceSetModuleBindingLocator,
) -> SourceSetModuleBindingSuppliedMember {
    let Some((member_key, member)) = handoff.members().iter().find(|(key, _)| {
        key.document() == locator.document && key.namespace() == locator.namespace
    }) else {
        return SourceSetModuleBindingSuppliedMember::Missing {
            target: locator.clone(),
        };
    };

    let structural_roots = member
        .prepared_source()
        .graph()
        .parts()
        .iter()
        .filter_map(|(address, part)| {
            matches!(part.containment, Containment::Root { root: true }).then_some(address.clone())
        })
        .collect::<Vec<_>>();
    assert_eq!(
        structural_roots.len(),
        1,
        "admitted member must have exactly one structural root"
    );
    let structural_root = structural_roots
        .into_iter()
        .next()
        .expect("exactly one structural root was admitted");
    SourceSetModuleBindingSuppliedMember::Supplied {
        member: member_key.clone(),
        role: member.role(),
        structural_root,
    }
}

fn instance_root_evidence(
    graph: &crate::body_graph::StructuralBodyGraph,
    module: &Module,
) -> Option<SourceSetModuleInstanceRoot> {
    if module.presence == Presence::Absent {
        return None;
    }
    let root = module
        .root
        .as_ref()
        .expect("admitted present module must have an instance root");
    let root = AddressKey::try_from(root).expect("admitted module root must be an AddressKey");
    let part = graph
        .parts()
        .get(&root)
        .expect("admitted module root must identify a Part");
    let parent = match &part.containment {
        Containment::Root { .. } => None,
        Containment::Parent { parent } => Some(
            AddressKey::try_from(parent).expect("admitted module parent must be an AddressKey"),
        ),
    };
    Some(SourceSetModuleInstanceRoot { root, parent })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::body_document::ResourceProfile;
    use crate::restricted_source_set_handoff::build_restricted_source_set_handoff;
    use crate::source_set_preparation::{SourceSetInput, prepare_source_set};
    use serde_json::Value;

    fn source(document: &str, namespace: &str) -> Vec<u8> {
        let mut value: Value = serde_json::from_slice(include_bytes!(
            "../../../examples/body-documents/stylized-digitigrade-biped.json"
        ))
        .expect("valid fixture");
        value["source"]["document"] = Value::String(document.into());
        value["source"]["namespace"] = Value::String(namespace.into());
        rewrite_namespaces(&mut value["body"], namespace);
        value["source"]["dependencies"] = Value::Array(Vec::new());
        serde_json::to_vec(&value).expect("serializes")
    }

    fn rewrite_namespaces(value: &mut Value, namespace: &str) {
        match value {
            Value::Object(object) => {
                if object.contains_key("namespace") {
                    object.insert("namespace".into(), Value::String(namespace.into()));
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
        let mut value: Value = serde_json::from_slice(source).unwrap();
        value["body"]["modules"][0]["declaration"]["document"] = document.into();
        value["body"]["modules"][0]["declaration"]["namespace"] = namespace.into();
        serde_json::to_vec(&value).unwrap()
    }

    fn with_dependencies(source: &[u8], dependencies: Vec<Value>) -> Vec<u8> {
        let mut value: Value = serde_json::from_slice(source).unwrap();
        value["source"]["dependencies"] = Value::Array(dependencies);
        serde_json::to_vec(&value).unwrap()
    }

    fn dependency(document: &str, namespace: &str, marker: char) -> Value {
        serde_json::json!({
            "document": document,
            "namespace": namespace,
            "content_sha256": format!("sha256:{}", marker.to_string().repeat(64)),
        })
    }

    fn handoff(
        root: &[u8],
        dependencies: Vec<&[u8]>,
    ) -> crate::restricted_source_set_handoff::RestrictedSourceSetHandoff {
        build_restricted_source_set_handoff(prepare_source_set(SourceSetInput::new(
            root,
            dependencies,
            ResourceProfile::ORDINARY,
        )))
        .unwrap()
    }

    #[test]
    fn present_module_retains_fields_and_evidence() {
        let dep = source("dep_doc", "dep_ns");
        let root = with_dependencies(
            &with_module_locator(&source("root_doc", "root_ns"), "dep_doc", "dep_ns"),
            vec![dependency("dep_doc", "dep_ns", 'a')],
        );
        let observed = observe_source_set_module_binding(&handoff(&root, vec![&dep]));
        let record = observed
            .records()
            .iter()
            .find(|record| record.owner().document() == "root_doc")
            .expect("root module record");
        assert_eq!(record.owner_role(), SourceSetMemberRole::Root);
        assert_eq!(record.module(), "tail");
        assert_eq!(record.root_role(), "tail_root");
        assert_eq!(record.instance_anchor(), "tail");
        assert_eq!(record.presence(), &Presence::Present);
        assert!(!record.optional());
        assert!(record.attachment_required());
        assert_eq!(record.declaration_provenance().member(), record.owner());
        assert_eq!(record.dependencies().len(), 1);
        assert_eq!(
            record.dependencies()[0].owner_role(),
            SourceSetMemberRole::Root
        );
        assert_eq!(
            record.dependencies()[0].owner_provenance().member(),
            record.owner()
        );
        assert_eq!(
            record.dependencies()[0].owner_provenance().role(),
            SourceSetMemberRole::Root
        );
        assert_eq!(
            record.dependencies()[0].dependency().content_sha256,
            format!("sha256:{}", "a".repeat(64))
        );
        assert!(record.supplied_member().member().is_some());
        assert_eq!(
            record.supplied_member().role(),
            Some(SourceSetMemberRole::Dependency)
        );
        assert_eq!(
            record.supplied_member().structural_root().unwrap().role(),
            "pelvis"
        );
        let instance = record.instance_root().unwrap();
        assert_eq!(instance.root().role(), "tail_root");
        assert_eq!(instance.parent().unwrap().role(), "pelvis");
    }

    #[test]
    fn absent_optional_module_has_no_instance_root_or_parent() {
        let mut value: Value = serde_json::from_slice(&source("root_doc", "root_ns")).unwrap();
        value["body"]["modules"][0]["presence"] = "absent".into();
        value["body"]["modules"][0]["optional"] = true.into();
        value["body"]["modules"][0]["attachment_required"] = false.into();
        value["body"]["attachments"] = Value::Array(Vec::new());
        value["body"]["modules"][0]
            .as_object_mut()
            .unwrap()
            .remove("root");
        let root = serde_json::to_vec(&value).unwrap();
        let observed = observe_source_set_module_binding(&handoff(&root, Vec::new()));
        let record = observed
            .records()
            .iter()
            .find(|record| record.owner().document() == "root_doc")
            .expect("root module record");
        assert_eq!(record.presence(), &Presence::Absent);
        assert!(record.instance_root().is_none());
    }

    #[test]
    fn missing_member_and_supplied_without_matching_owner_edge_are_distinct() {
        let missing =
            with_module_locator(&source("root_doc", "root_ns"), "missing_doc", "missing_ns");
        let missing_observation = observe_source_set_module_binding(&handoff(&missing, Vec::new()));
        let missing_record = missing_observation
            .records()
            .iter()
            .find(|record| record.owner().document() == "root_doc")
            .expect("root module record");
        assert!(matches!(
            missing_record.supplied_member(),
            SourceSetModuleBindingSuppliedMember::Missing { .. }
        ));

        let dep = source("dep_doc", "dep_ns");
        let supplied = with_module_locator(&source("root_doc", "root_ns"), "dep_doc", "dep_ns");
        let supplied_observation =
            observe_source_set_module_binding(&handoff(&supplied, vec![&dep]));
        let supplied_record = supplied_observation
            .records()
            .iter()
            .find(|record| record.owner().document() == "root_doc")
            .expect("root module record");
        assert!(supplied_record.dependencies().is_empty());
        assert!(matches!(
            supplied_record.supplied_member(),
            SourceSetModuleBindingSuppliedMember::Supplied { .. }
        ));
    }

    #[test]
    fn multiple_modules_and_member_input_permutations_compare_equal() {
        let first = source("dep_a", "ns_a");
        let second = source("dep_b", "ns_b");
        let mut root_value: Value = serde_json::from_slice(&with_module_locator(
            &source("root_doc", "root_ns"),
            "dep_a",
            "ns_a",
        ))
        .unwrap();
        let mut second_module = root_value["body"]["modules"][0].clone();
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
        let root = with_dependencies(
            &serde_json::to_vec(&root_value).unwrap(),
            vec![dependency("dep_a", "ns_a", 'a')],
        );
        let forward = observe_source_set_module_binding(&handoff(&root, vec![&first, &second]));
        let reverse = observe_source_set_module_binding(&handoff(&root, vec![&second, &first]));
        assert_eq!(forward, reverse);
        assert_eq!(forward.records().len(), 4);
        let matching_root_modules = forward
            .records()
            .iter()
            .filter(|record| {
                record.owner().document() == "root_doc"
                    && record.locator().document() == "dep_a"
                    && record.locator().namespace() == "ns_a"
            })
            .collect::<Vec<_>>();
        assert_eq!(matching_root_modules.len(), 2);
        assert!(
            matching_root_modules
                .iter()
                .all(|record| record.dependencies().len() == 1)
        );
    }
}
