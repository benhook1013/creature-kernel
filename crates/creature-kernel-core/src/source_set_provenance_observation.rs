//! Crate-private deterministic source-set provenance and topology observation.
//!
//! This projection inventories the source-local identities and ownership that
//! are already present in a [`RestrictedSourceSetHandoff`].  It also walks the
//! handoff's locator-only dependency graph from its root.  The projection is
//! deliberately observational: it does not verify declared revisions or
//! hashes, acquire source bytes, merge or remap namespaces, resolve semantic
//! references, or classify resolver statuses.

#![allow(dead_code)]

use crate::body_graph::{ModuleDeclarationKey, OwnerRoleKey};
use crate::restricted_source_set_handoff::RestrictedSourceSetHandoff;
use crate::semantic_address::AddressKey;
use crate::source_set_preparation::{
    SourceSetDependencyEdge, SourceSetMemberKey, SourceSetMemberRole,
};
use std::collections::{BTreeMap, BTreeSet};

/// Provenance retained for one indexed source-local record.
///
/// The member key is repeated in each indexed value intentionally.  A caller
/// inspecting a record does not need to infer ownership from the containing
/// map alone, and the member role remains explicit alongside the ownership.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct SourceSetRecordProvenance {
    member: SourceSetMemberKey,
    role: SourceSetMemberRole,
}

impl SourceSetRecordProvenance {
    /// Owning source-set member.
    #[must_use]
    pub(crate) fn member(&self) -> &SourceSetMemberKey {
        &self.member
    }

    /// Root/dependency role of the owning source-set member.
    #[must_use]
    pub(crate) const fn role(&self) -> SourceSetMemberRole {
        self.role
    }
}

/// Typed source-local owner/role record kind.
///
/// Landmark, dimension, and named-frame records share an [`OwnerRoleKey`], so
/// the kind is retained as a second map key rather than silently collapsing
/// records that happen to use the same owner and role.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub(crate) enum SourceSetOwnerRoleRecordKind {
    /// Authored landmark record.
    Landmark,
    /// Authored dimension record.
    Dimension,
    /// Authored named-frame record.
    Frame,
}

/// Deterministic source-local provenance inventory for one member.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct SourceSetMemberProvenance {
    key: SourceSetMemberKey,
    role: SourceSetMemberRole,
    semantic_addresses: BTreeMap<AddressKey, SourceSetRecordProvenance>,
    module_declarations: BTreeMap<ModuleDeclarationKey, SourceSetRecordProvenance>,
    owner_roles:
        BTreeMap<OwnerRoleKey, BTreeMap<SourceSetOwnerRoleRecordKind, SourceSetRecordProvenance>>,
}

impl SourceSetMemberProvenance {
    /// Stable source-set member key.
    #[must_use]
    pub(crate) fn key(&self) -> &SourceSetMemberKey {
        &self.key
    }

    /// Root/dependency role retained from the handoff.
    #[must_use]
    pub(crate) const fn role(&self) -> SourceSetMemberRole {
        self.role
    }

    /// Source-local identity-bearing semantic addresses.
    #[must_use]
    pub(crate) fn semantic_addresses(&self) -> &BTreeMap<AddressKey, SourceSetRecordProvenance> {
        &self.semantic_addresses
    }

    /// Alias for callers that describe these keys simply as addresses.
    #[must_use]
    pub(crate) fn addresses(&self) -> &BTreeMap<AddressKey, SourceSetRecordProvenance> {
        self.semantic_addresses()
    }

    /// Source-local module declaration keys.
    #[must_use]
    pub(crate) fn module_declarations(
        &self,
    ) -> &BTreeMap<ModuleDeclarationKey, SourceSetRecordProvenance> {
        &self.module_declarations
    }

    /// Source-local owner/role records, retaining their typed record kind.
    #[must_use]
    pub(crate) fn owner_roles(
        &self,
    ) -> &BTreeMap<OwnerRoleKey, BTreeMap<SourceSetOwnerRoleRecordKind, SourceSetRecordProvenance>>
    {
        &self.owner_roles
    }

    /// Alias emphasizing that these are records rather than graph addresses.
    #[must_use]
    pub(crate) fn owner_role_records(
        &self,
    ) -> &BTreeMap<OwnerRoleKey, BTreeMap<SourceSetOwnerRoleRecordKind, SourceSetRecordProvenance>>
    {
        self.owner_roles()
    }
}

/// One declared dependency occurrence with explicit owning-member provenance.
///
/// The complete original declaration edge is retained, including opaque
/// `content_sha256` text.  `supplied_target` is present only when the existing
/// handoff locator projection found a supplied member with that key.  The
/// locator key itself is always available through [`Self::target`].
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct SourceSetDependencyEdgeObservation {
    edge: SourceSetDependencyEdge,
    owner_role: SourceSetMemberRole,
    supplied_target: Option<SourceSetMemberKey>,
}

impl SourceSetDependencyEdgeObservation {
    /// Complete retained declaration edge.
    #[must_use]
    pub(crate) fn edge(&self) -> &SourceSetDependencyEdge {
        &self.edge
    }

    /// Owning source-set member key.
    #[must_use]
    pub(crate) fn owner(&self) -> &SourceSetMemberKey {
        self.edge.owner()
    }

    /// Owning source-set member role.
    #[must_use]
    pub(crate) const fn owner_role(&self) -> SourceSetMemberRole {
        self.owner_role
    }

    /// Dependency declaration, including its opaque revision/hash text.
    #[must_use]
    pub(crate) fn dependency(&self) -> &crate::body_document::Dependency {
        self.edge.dependency()
    }

    /// Locator key named by this declaration, whether supplied or missing.
    #[must_use]
    pub(crate) fn target(&self) -> SourceSetMemberKey {
        self.edge.locator_key()
    }

    /// Supplied member matched by the existing locator-only projection.
    #[must_use]
    pub(crate) fn supplied_target(&self) -> Option<&SourceSetMemberKey> {
        self.supplied_target.as_ref()
    }
}

/// Topology-only classification for one reached dependency edge.
///
/// These variants are observations of supplied locator topology.  In
/// particular, [`Self::BackEdge`] is not a resolver diagnostic or status.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub(crate) enum SourceSetDependencyTraversalKind {
    /// The target was supplied and this edge was reached from the root.
    Reached,
    /// The target locator was reached but no supplied member had that key.
    MissingSuppliedTarget,
    /// The supplied target was active on the current traversal stack.
    BackEdge,
}

/// One reached dependency edge and its topology-only observation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct SourceSetDependencyTraversalEdge {
    declaration: SourceSetDependencyEdgeObservation,
    kind: SourceSetDependencyTraversalKind,
}

impl SourceSetDependencyTraversalEdge {
    /// Underlying declaration occurrence.
    #[must_use]
    pub(crate) fn declaration(&self) -> &SourceSetDependencyEdgeObservation {
        &self.declaration
    }

    /// Complete retained declaration edge.
    #[must_use]
    pub(crate) fn edge(&self) -> &SourceSetDependencyEdge {
        self.declaration.edge()
    }

    /// Owning source-set member key.
    #[must_use]
    pub(crate) fn owner(&self) -> &SourceSetMemberKey {
        self.declaration.owner()
    }

    /// Owning source-set member role.
    #[must_use]
    pub(crate) const fn owner_role(&self) -> SourceSetMemberRole {
        self.declaration.owner_role()
    }

    /// Locator key named by this declaration.
    #[must_use]
    pub(crate) fn target(&self) -> SourceSetMemberKey {
        self.declaration.target()
    }

    /// Supplied target, when the locator-only projection found one.
    #[must_use]
    pub(crate) fn supplied_target(&self) -> Option<&SourceSetMemberKey> {
        self.declaration.supplied_target()
    }

    /// Topology-only edge classification.
    #[must_use]
    pub(crate) const fn kind(&self) -> SourceSetDependencyTraversalKind {
        self.kind
    }
}

/// Deterministic source-set provenance and dependency-topology observation.
///
/// This is an owned, crate-private projection.  Member inventories and
/// namespace owners are keyed by stable ordered collections.  Dependency
/// vectors preserve every declaration occurrence; duplicate declarations are
/// never deduplicated merely because their fields compare equal.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct SourceSetProvenanceObservation {
    root: SourceSetMemberKey,
    members: BTreeMap<SourceSetMemberKey, SourceSetMemberProvenance>,
    semantic_address_occurrences: BTreeMap<AddressKey, Vec<SourceSetRecordProvenance>>,
    semantic_address_collisions: BTreeSet<AddressKey>,
    namespace_owners: BTreeMap<String, BTreeSet<SourceSetMemberKey>>,
    namespace_collisions: BTreeMap<String, BTreeSet<SourceSetMemberKey>>,
    declared_dependency_edges: Vec<SourceSetDependencyEdgeObservation>,
    traversed_dependency_edges: Vec<SourceSetDependencyTraversalEdge>,
    all_missing_supplied_targets: Vec<SourceSetDependencyEdgeObservation>,
    back_edges: Vec<SourceSetDependencyTraversalEdge>,
    reached_members: BTreeSet<SourceSetMemberKey>,
    unreachable_members: BTreeSet<SourceSetMemberKey>,
}

impl SourceSetProvenanceObservation {
    /// Root member key retained from the handoff.
    #[must_use]
    pub(crate) fn root(&self) -> &SourceSetMemberKey {
        &self.root
    }

    /// Deterministically keyed member provenance inventories.
    #[must_use]
    pub(crate) fn members(&self) -> &BTreeMap<SourceSetMemberKey, SourceSetMemberProvenance> {
        &self.members
    }

    /// Every admitted occurrence of each source-local semantic address.
    ///
    /// The vectors retain all member provenance rather than selecting an
    /// owner or deduplicating equal keys.  Their order is deterministic:
    /// members are visited by [`SourceSetMemberKey`] order and each member's
    /// address inventory is already address-key ordered.  This is an
    /// observation-only projection; it does not assign canonical occurrence
    /// identity or resolver status.
    #[must_use]
    pub(crate) fn semantic_address_occurrences(
        &self,
    ) -> &BTreeMap<AddressKey, Vec<SourceSetRecordProvenance>> {
        &self.semantic_address_occurrences
    }

    /// Address entries with more than one retained occurrence.
    ///
    /// This is a projection of [`Self::semantic_address_occurrences`], not a
    /// rejection or ownership decision.  Full provenance remains available
    /// only through [`Self::semantic_address_occurrences`].
    #[must_use]
    pub(crate) fn semantic_address_collisions(&self) -> &BTreeSet<AddressKey> {
        &self.semantic_address_collisions
    }

    /// Namespace to all admitted member owners.
    ///
    /// A namespace may intentionally have multiple owners in this observation
    /// when documents differ.  No collision is rejected, selected, merged, or
    /// remapped here.
    #[must_use]
    pub(crate) fn namespace_owners(&self) -> &BTreeMap<String, BTreeSet<SourceSetMemberKey>> {
        &self.namespace_owners
    }

    /// Only namespace entries with more than one distinct member owner.
    #[must_use]
    pub(crate) fn namespace_collisions(&self) -> &BTreeMap<String, BTreeSet<SourceSetMemberKey>> {
        &self.namespace_collisions
    }

    /// Every supplied declaration occurrence in deterministic edge order.
    #[must_use]
    pub(crate) fn declared_dependency_edges(&self) -> &[SourceSetDependencyEdgeObservation] {
        &self.declared_dependency_edges
    }

    /// Alias for callers that use the shorter edge terminology.
    #[must_use]
    pub(crate) fn dependency_edges(&self) -> &[SourceSetDependencyEdgeObservation] {
        self.declared_dependency_edges()
    }

    /// Dependency declarations reached by root-started traversal, including
    /// reached missing targets and topology-only back-edges.
    #[must_use]
    pub(crate) fn traversed_dependency_edges(&self) -> &[SourceSetDependencyTraversalEdge] {
        &self.traversed_dependency_edges
    }

    /// All declared occurrences whose locators had no supplied target.
    ///
    /// This includes a missing declaration owned by a supplied-but-unreachable
    /// member, so the observation never hides an already-admitted missing
    /// locator outcome.
    #[must_use]
    pub(crate) fn all_missing_supplied_targets(&self) -> &[SourceSetDependencyEdgeObservation] {
        &self.all_missing_supplied_targets
    }

    /// Topology-only active-stack back-edge observations.
    #[must_use]
    pub(crate) fn back_edges(&self) -> &[SourceSetDependencyTraversalEdge] {
        &self.back_edges
    }

    /// Alias emphasizing that back-edges are cycle topology evidence only.
    #[must_use]
    pub(crate) fn cycle_back_edges(&self) -> &[SourceSetDependencyTraversalEdge] {
        self.back_edges()
    }

    /// Members reached from the root through supplied targets.
    #[must_use]
    pub(crate) fn reached_members(&self) -> &BTreeSet<SourceSetMemberKey> {
        &self.reached_members
    }

    /// Supplied members not reached by the root-started traversal.
    #[must_use]
    pub(crate) fn unreachable_members(&self) -> &BTreeSet<SourceSetMemberKey> {
        &self.unreachable_members
    }
}

/// Observe source-local provenance and supplied dependency topology.
///
/// Only already-admitted handoff data is read.  No status, diagnostic,
/// resolution, verification, acquisition, namespace remap, canonical digest,
/// or snapshot operation is performed.
pub(crate) fn observe_source_set_provenance(
    handoff: &RestrictedSourceSetHandoff,
) -> SourceSetProvenanceObservation {
    let mut members = BTreeMap::new();
    let mut semantic_address_occurrences: BTreeMap<AddressKey, Vec<SourceSetRecordProvenance>> =
        BTreeMap::new();
    let mut namespace_owners: BTreeMap<String, BTreeSet<SourceSetMemberKey>> = BTreeMap::new();

    for (key, member) in handoff.members() {
        let inventory = member_provenance(key, member.role(), member.prepared_source().graph());
        for (address, provenance) in inventory.semantic_addresses() {
            semantic_address_occurrences
                .entry(address.clone())
                .or_default()
                .push(provenance.clone());
        }
        namespace_owners
            .entry(key.namespace().to_owned())
            .or_default()
            .insert(key.clone());
        debug_assert!(members.insert(key.clone(), inventory).is_none());
    }

    let namespace_collisions = namespace_owners
        .iter()
        .filter(|(_, owners)| owners.len() > 1)
        .map(|(namespace, owners)| (namespace.clone(), owners.clone()))
        .collect();

    let semantic_address_collisions = semantic_address_occurrences
        .iter()
        .filter(|(_, occurrences)| occurrences.len() > 1)
        .map(|(address, _)| address.clone())
        .collect();

    let declared_dependency_edges = handoff
        .dependency_locator_results()
        .iter()
        .map(|result| {
            let owner_role = handoff
                .members()
                .get(result.edge().owner())
                .expect("handoff validates every dependency edge owner")
                .role();
            SourceSetDependencyEdgeObservation {
                edge: result.edge().clone(),
                owner_role,
                supplied_target: result.target().cloned(),
            }
        })
        .collect::<Vec<_>>();

    let all_missing_supplied_targets = declared_dependency_edges
        .iter()
        .filter(|edge| edge.supplied_target().is_none())
        .cloned()
        .collect::<Vec<_>>();

    let mut adjacency: BTreeMap<SourceSetMemberKey, Vec<usize>> = BTreeMap::new();
    for (index, edge) in declared_dependency_edges.iter().enumerate() {
        adjacency
            .entry(edge.owner().clone())
            .or_default()
            .push(index);
    }
    for edge_indices in adjacency.values_mut() {
        edge_indices.sort_by(|left, right| {
            declared_dependency_edges[*left]
                .edge()
                .cmp(declared_dependency_edges[*right].edge())
        });
    }

    let mut reached_members = BTreeSet::new();
    let mut visit_state = BTreeMap::new();
    let mut traversed_dependency_edges = Vec::new();
    let mut back_edges = Vec::new();
    traverse_dependency_graph(
        handoff.root(),
        &adjacency,
        &declared_dependency_edges,
        &mut visit_state,
        &mut reached_members,
        &mut traversed_dependency_edges,
        &mut back_edges,
    );

    let unreachable_members = handoff
        .members()
        .keys()
        .filter(|key| !reached_members.contains(*key))
        .cloned()
        .collect();

    SourceSetProvenanceObservation {
        root: handoff.root().clone(),
        members,
        semantic_address_occurrences,
        semantic_address_collisions,
        namespace_owners,
        namespace_collisions,
        declared_dependency_edges,
        traversed_dependency_edges,
        all_missing_supplied_targets,
        back_edges,
        reached_members,
        unreachable_members,
    }
}

fn member_provenance(
    key: &SourceSetMemberKey,
    role: SourceSetMemberRole,
    graph: &crate::body_graph::StructuralBodyGraph,
) -> SourceSetMemberProvenance {
    let record_provenance = || SourceSetRecordProvenance {
        member: key.clone(),
        role,
    };
    let mut semantic_addresses = BTreeMap::new();
    for address in graph.parts().keys() {
        semantic_addresses.insert(address.clone(), record_provenance());
    }
    for address in graph.joints().keys() {
        semantic_addresses.insert(address.clone(), record_provenance());
    }
    for address in graph.sockets().keys() {
        semantic_addresses.insert(address.clone(), record_provenance());
    }
    for address in graph.attachments().keys() {
        semantic_addresses.insert(address.clone(), record_provenance());
    }
    for address in graph.regions().keys() {
        semantic_addresses.insert(address.clone(), record_provenance());
    }
    for address in graph.capabilities().keys() {
        semantic_addresses.insert(address.clone(), record_provenance());
    }
    for address in graph.fields().keys() {
        semantic_addresses.insert(address.clone(), record_provenance());
    }

    let module_declarations = graph
        .modules()
        .keys()
        .map(|declaration| (declaration.clone(), record_provenance()))
        .collect();

    let mut owner_roles: BTreeMap<
        OwnerRoleKey,
        BTreeMap<SourceSetOwnerRoleRecordKind, SourceSetRecordProvenance>,
    > = BTreeMap::new();
    for owner_role in graph.landmarks().keys() {
        owner_roles
            .entry(owner_role.clone())
            .or_default()
            .insert(SourceSetOwnerRoleRecordKind::Landmark, record_provenance());
    }
    for owner_role in graph.dimensions().keys() {
        owner_roles
            .entry(owner_role.clone())
            .or_default()
            .insert(SourceSetOwnerRoleRecordKind::Dimension, record_provenance());
    }
    for owner_role in graph.frames().keys() {
        owner_roles
            .entry(owner_role.clone())
            .or_default()
            .insert(SourceSetOwnerRoleRecordKind::Frame, record_provenance());
    }

    SourceSetMemberProvenance {
        key: key.clone(),
        role,
        semantic_addresses,
        module_declarations,
        owner_roles,
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum VisitState {
    Active,
    Complete,
}

/// Traverse the already-classified supplied locator graph with an explicit
/// depth-first stack.  The stack is intentionally not bounded by a source-set
/// aggregate limit: any bound belongs to a later resolver/resource contract,
/// not this topology observation.
fn traverse_dependency_graph(
    current: &SourceSetMemberKey,
    adjacency: &BTreeMap<SourceSetMemberKey, Vec<usize>>,
    declared_edges: &[SourceSetDependencyEdgeObservation],
    visit_state: &mut BTreeMap<SourceSetMemberKey, VisitState>,
    reached_members: &mut BTreeSet<SourceSetMemberKey>,
    traversed_dependency_edges: &mut Vec<SourceSetDependencyTraversalEdge>,
    back_edges: &mut Vec<SourceSetDependencyTraversalEdge>,
) {
    struct Frame {
        member: SourceSetMemberKey,
        next_edge: usize,
    }

    visit_state.insert(current.clone(), VisitState::Active);
    reached_members.insert(current.clone());
    let mut stack = vec![Frame {
        member: current.clone(),
        next_edge: 0,
    }];

    while !stack.is_empty() {
        let edge_index = {
            let frame = stack.last_mut().expect("non-empty traversal stack");
            match adjacency.get(&frame.member) {
                Some(edge_indices) if frame.next_edge < edge_indices.len() => {
                    let edge_index = edge_indices[frame.next_edge];
                    frame.next_edge += 1;
                    Some(edge_index)
                }
                _ => None,
            }
        };

        let Some(edge_index) = edge_index else {
            let frame = stack.pop().expect("non-empty traversal stack");
            visit_state.insert(frame.member, VisitState::Complete);
            continue;
        };

        let declaration = &declared_edges[edge_index];
        let kind = match declaration.supplied_target() {
            None => SourceSetDependencyTraversalKind::MissingSuppliedTarget,
            Some(target) => match visit_state.get(target) {
                Some(VisitState::Active) => SourceSetDependencyTraversalKind::BackEdge,
                Some(VisitState::Complete) | None => SourceSetDependencyTraversalKind::Reached,
            },
        };
        let traversal = SourceSetDependencyTraversalEdge {
            declaration: declaration.clone(),
            kind,
        };
        traversed_dependency_edges.push(traversal.clone());
        if kind == SourceSetDependencyTraversalKind::BackEdge {
            back_edges.push(traversal);
            continue;
        }

        let Some(target) = declaration.supplied_target() else {
            continue;
        };
        if visit_state.contains_key(target) {
            continue;
        }
        visit_state.insert(target.clone(), VisitState::Active);
        reached_members.insert(target.clone());
        stack.push(Frame {
            member: target.clone(),
            next_edge: 0,
        });
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::body_document::ResourceProfile;
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

    fn source_with_owner_roles(document: &str, namespace: &str) -> Vec<u8> {
        let mut value: Value =
            serde_json::from_slice(&source(document, namespace)).expect("source is valid JSON");
        let owner = value["body"]["parts"][0]["address"].clone();
        let transform = serde_json::json!({
            "translation": [0, 0, 0],
            "rotation_xyzw": [0, 0, 0, 1]
        });
        value["body"]["frames"] = serde_json::json!([{
            "owner": owner,
            "role": "shared_role",
            "transform": transform
        }]);
        value["body"]["landmarks"] = serde_json::json!([{
            "owner": value["body"]["parts"][0]["address"].clone(),
            "role": "shared_role",
            "frame": {
                "owner": value["body"]["parts"][0]["address"].clone(),
                "role": "shared_role"
            },
            "position": [0, 0, 0]
        }]);
        value["body"]["dimensions"] = serde_json::json!([{
            "owner": value["body"]["parts"][0]["address"].clone(),
            "role": "shared_role",
            "value": 1
        }]);
        serde_json::to_vec(&value).expect("source serializes")
    }

    fn source_with_capability_role(document: &str, namespace: &str, role: &str) -> Vec<u8> {
        let mut value: Value =
            serde_json::from_slice(&source(document, namespace)).expect("source is valid JSON");
        value["body"]["capabilities"][0]["address"]["role"] = Value::String(role.to_owned());
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

    #[test]
    fn root_dependency_leaf_inventory_retains_member_provenance() {
        let root = with_dependencies(
            &source_with_owner_roles("root_doc", "root_ns"),
            serde_json::json!([declaration("dep_doc", "dep_ns", 'a')]),
        );
        let dependency = with_dependencies(
            &source("dep_doc", "dep_ns"),
            serde_json::json!([declaration("leaf_doc", "leaf_ns", 'b')]),
        );
        let leaf = source("leaf_doc", "leaf_ns");
        let observation = observe_source_set_provenance(&handoff(&root, vec![&dependency, &leaf]));

        assert_eq!(observation.reached_members().len(), 3);
        assert!(observation.unreachable_members().is_empty());
        assert_eq!(observation.traversed_dependency_edges().len(), 2);
        let root_inventory = &observation.members()[observation.root()];
        assert_eq!(root_inventory.role(), SourceSetMemberRole::Root);
        assert!(!root_inventory.semantic_addresses().is_empty());
        assert!(!root_inventory.module_declarations().is_empty());
        let owner_role_records = root_inventory
            .owner_roles()
            .values()
            .next()
            .expect("owner-role records exist");
        assert_eq!(
            owner_role_records.keys().copied().collect::<Vec<_>>(),
            vec![
                SourceSetOwnerRoleRecordKind::Landmark,
                SourceSetOwnerRoleRecordKind::Dimension,
                SourceSetOwnerRoleRecordKind::Frame,
            ]
        );
        assert_eq!(owner_role_records.len(), 3);
        for record in root_inventory.semantic_addresses().values() {
            assert_eq!(record.member(), observation.root());
            assert_eq!(record.role(), SourceSetMemberRole::Root);
        }
        for record in root_inventory.module_declarations().values() {
            assert_eq!(record.member(), observation.root());
            assert_eq!(record.role(), SourceSetMemberRole::Root);
        }
        for records in root_inventory.owner_roles().values() {
            for record in records.values() {
                assert_eq!(record.member(), observation.root());
                assert_eq!(record.role(), SourceSetMemberRole::Root);
            }
        }
        for edge in observation.traversed_dependency_edges() {
            assert_eq!(
                edge.owner_role(),
                observation.members()[edge.owner()].role()
            );
        }
    }

    #[test]
    fn missing_target_is_retained_without_status_or_panic() {
        let root = with_dependencies(
            &source("root_doc", "root_ns"),
            serde_json::json!([declaration("missing_doc", "missing_ns", 'a')]),
        );
        let observation = observe_source_set_provenance(&handoff(&root, Vec::new()));

        assert_eq!(observation.all_missing_supplied_targets().len(), 1);
        assert_eq!(
            observation.all_missing_supplied_targets()[0]
                .target()
                .document(),
            "missing_doc"
        );
        assert_eq!(
            observation.traversed_dependency_edges()[0].kind(),
            SourceSetDependencyTraversalKind::MissingSuppliedTarget
        );
        assert!(observation.unreachable_members().is_empty());
    }

    #[test]
    fn cycle_retains_back_edge_without_infinite_traversal() {
        let root = with_dependencies(
            &source("root_doc", "root_ns"),
            serde_json::json!([declaration("dep_doc", "dep_ns", 'a')]),
        );
        let dependency = with_dependencies(
            &source("dep_doc", "dep_ns"),
            serde_json::json!([declaration("root_doc", "root_ns", 'b')]),
        );
        let observation = observe_source_set_provenance(&handoff(&root, vec![&dependency]));

        assert_eq!(observation.reached_members().len(), 2);
        assert_eq!(observation.traversed_dependency_edges().len(), 2);
        assert_eq!(observation.back_edges().len(), 1);
        assert_eq!(
            observation.back_edges()[0].kind(),
            SourceSetDependencyTraversalKind::BackEdge
        );
        assert_eq!(
            observation.back_edges()[0].target(),
            observation.root().clone()
        );
    }

    #[test]
    fn duplicate_namespace_documents_remain_multiple_namespace_owners() {
        let root = source("root_doc", "shared_ns");
        let first = source("first_doc", "shared_ns");
        let second = source("second_doc", "shared_ns");
        let observation = observe_source_set_provenance(&handoff(&root, vec![&second, &first]));

        let owners = &observation.namespace_owners()["shared_ns"];
        assert_eq!(owners.len(), 3);
        assert_eq!(observation.namespace_collisions()["shared_ns"], *owners);
        assert!(owners.iter().any(|owner| owner.document() == "first_doc"));
        assert!(owners.iter().any(|owner| owner.document() == "second_doc"));
    }

    #[test]
    fn semantic_address_occurrences_retain_same_key_and_project_collisions() {
        let root = source("root_doc", "root_ns");
        let first = source("first_doc", "shared_ns");
        let second = source("second_doc", "shared_ns");
        let observation = observe_source_set_provenance(&handoff(&root, vec![&second, &first]));
        let address = observation
            .members()
            .values()
            .find(|member| member.key().document() == "first_doc")
            .expect("first member is admitted")
            .semantic_addresses()
            .keys()
            .next()
            .expect("shared member has an address")
            .clone();

        let occurrences = &observation.semantic_address_occurrences()[&address];
        assert_eq!(occurrences.len(), 2);
        assert_eq!(
            occurrences
                .iter()
                .map(|occurrence| occurrence.member().document())
                .collect::<Vec<_>>(),
            vec!["first_doc", "second_doc"]
        );
        assert!(observation.semantic_address_collisions().contains(&address));
        assert_eq!(observation.namespace_collisions()["shared_ns"].len(), 2);
        assert!(
            observation
                .semantic_address_collisions()
                .iter()
                .all(|address| observation.semantic_address_occurrences()[address].len() > 1)
        );
    }

    #[test]
    fn semantic_address_occurrences_are_input_order_independent() {
        let root = source("root_doc", "root_ns");
        let first = source("first_doc", "shared_ns");
        let second = source("second_doc", "shared_ns");
        let forward = observe_source_set_provenance(&handoff(&root, vec![&first, &second]));
        let reversed = observe_source_set_provenance(&handoff(&root, vec![&second, &first]));

        assert_eq!(
            forward.semantic_address_occurrences(),
            reversed.semantic_address_occurrences()
        );
        assert_eq!(
            forward.semantic_address_collisions(),
            reversed.semantic_address_collisions()
        );
    }

    #[test]
    fn disjoint_namespaced_addresses_have_no_false_collisions() {
        let root = source("root_doc", "root_ns");
        let dependency = source("dependency_doc", "dependency_ns");
        let observation = observe_source_set_provenance(&handoff(&root, vec![&dependency]));

        assert!(!observation.semantic_address_occurrences().is_empty());
        assert!(observation.semantic_address_collisions().is_empty());
    }

    #[test]
    fn same_namespace_collision_projection_excludes_distinct_address_keys() {
        let root = source("root_doc", "root_ns");
        let first = source("first_doc", "shared_ns");
        let second = source_with_capability_role("second_doc", "shared_ns", "alternate");
        let observation = observe_source_set_provenance(&handoff(&root, vec![&second, &first]));
        let first_inventory = observation
            .members()
            .values()
            .find(|member| member.key().document() == "first_doc")
            .expect("first member is admitted");
        let second_inventory = observation
            .members()
            .values()
            .find(|member| member.key().document() == "second_doc")
            .expect("second member is admitted");
        let expected_intersection = first_inventory
            .semantic_addresses()
            .keys()
            .filter(|address| second_inventory.semantic_addresses().contains_key(*address))
            .cloned()
            .collect::<BTreeSet<_>>();

        assert_eq!(observation.namespace_collisions()["shared_ns"].len(), 2);
        assert_eq!(
            observation.semantic_address_collisions(),
            &expected_intersection
        );
        assert!(
            first_inventory
                .semantic_addresses()
                .keys()
                .filter(|address| !second_inventory.semantic_addresses().contains_key(*address))
                .all(|address| !observation.semantic_address_collisions().contains(address))
        );
    }

    #[test]
    fn member_and_declaration_order_are_deterministic_and_duplicate_edges_remain() {
        let root_a = with_dependencies(
            &source("root_doc", "root_ns"),
            serde_json::json!([
                declaration("owner_a", "owner_a_ns", 'a'),
                declaration("owner_b", "owner_b_ns", 'a')
            ]),
        );
        let root_b = with_dependencies(
            &source("root_doc", "root_ns"),
            serde_json::json!([
                declaration("owner_b", "owner_b_ns", 'a'),
                declaration("owner_a", "owner_a_ns", 'a')
            ]),
        );
        let owner_a = with_dependencies(
            &source("owner_a", "owner_a_ns"),
            serde_json::json!([declaration("shared_doc", "shared_ns", 'b')]),
        );
        let owner_b = with_dependencies(
            &source("owner_b", "owner_b_ns"),
            serde_json::json!([declaration("shared_doc", "shared_ns", 'b')]),
        );
        let shared = source("shared_doc", "shared_ns");
        let first =
            observe_source_set_provenance(&handoff(&root_a, vec![&owner_b, &shared, &owner_a]));
        let second =
            observe_source_set_provenance(&handoff(&root_b, vec![&owner_a, &owner_b, &shared]));

        assert_eq!(first, second);
        assert_eq!(first.declared_dependency_edges().len(), 4);
        assert_eq!(first.traversed_dependency_edges().len(), 4);
        assert_eq!(
            first
                .declared_dependency_edges()
                .iter()
                .filter(|edge| edge.target().namespace() == "shared_ns")
                .count(),
            2
        );
    }

    #[test]
    fn identical_repeated_declarations_from_one_owner_remain_two_traversed_occurrences() {
        // The admitted body-document structural contract rejects duplicate
        // dependency namespaces before handoff construction.  Duplicate
        // occurrences are nevertheless valid input to this observation's
        // lower-level graph walk, so exercise that walk directly with two
        // identical occurrences copied from one root-owned supplied edge.
        let root = with_dependencies(
            &source("root_doc", "root_ns"),
            serde_json::json!([declaration("dep_doc", "dep_ns", 'a')]),
        );
        let dependency = source("dep_doc", "dep_ns");
        let baseline = observe_source_set_provenance(&handoff(&root, vec![&dependency]));
        let edge = baseline
            .declared_dependency_edges()
            .first()
            .expect("root dependency edge exists")
            .clone();
        let declared = vec![edge.clone(), edge];
        let mut adjacency = BTreeMap::new();
        adjacency.insert(declared[0].owner().clone(), vec![0, 1]);
        let mut visit_state = BTreeMap::new();
        let mut reached_members = BTreeSet::new();
        let mut traversed_dependency_edges = Vec::new();
        let mut back_edges = Vec::new();

        traverse_dependency_graph(
            baseline.root(),
            &adjacency,
            &declared,
            &mut visit_state,
            &mut reached_members,
            &mut traversed_dependency_edges,
            &mut back_edges,
        );

        assert_eq!(declared.len(), 2);
        assert_eq!(traversed_dependency_edges.len(), 2);
        assert_eq!(back_edges.len(), 0);
        assert_eq!(reached_members.len(), 2);
        assert!(traversed_dependency_edges.iter().all(|edge| {
            edge.kind() == SourceSetDependencyTraversalKind::Reached
                && edge.owner() == baseline.root()
                && edge.supplied_target().is_some()
        }));
        assert_eq!(
            traversed_dependency_edges[0].declaration(),
            traversed_dependency_edges[1].declaration()
        );
    }

    #[test]
    fn supplied_but_unreachable_member_is_retained_explicitly() {
        let root = with_dependencies(
            &source("root_doc", "root_ns"),
            serde_json::json!([declaration("reachable_doc", "reachable_ns", 'a')]),
        );
        let reachable = source("reachable_doc", "reachable_ns");
        let unreachable = with_dependencies(
            &source("unreachable_doc", "unreachable_ns"),
            serde_json::json!([declaration("missing_doc", "missing_ns", 'b')]),
        );
        let observation =
            observe_source_set_provenance(&handoff(&root, vec![&unreachable, &reachable]));

        assert!(
            observation
                .unreachable_members()
                .iter()
                .any(|key| key.document() == "unreachable_doc")
        );
        assert_eq!(observation.reached_members().len(), 2);
        assert_eq!(observation.all_missing_supplied_targets().len(), 1);
        assert_eq!(observation.traversed_dependency_edges().len(), 1);
    }
}
