//! Crate-private candidate projection of a source set into destination
//! namespaces.
//!
//! This is an in-memory algorithm observation over existing provenance.  It
//! replaces only the namespace component of semantic and owner-role keys,
//! retains all occurrences, and reports collisions without selecting or
//! merging them.  Module declaration keys remain unchanged companion
//! bookkeeping because their namespace identifies the declared module source.
//! It does not rewrite authored references or claim a resolved graph.

#![allow(dead_code)]

use crate::body_document::Address;
use crate::body_graph::{ModuleDeclarationKey, OwnerRoleKey};
use crate::semantic_address::{AddressKey, is_identifier};
use crate::source_set_preparation::SourceSetMemberKey;
use crate::source_set_provenance_observation::{
    SourceSetOwnerRoleRecordKind, SourceSetProvenanceObservation, SourceSetRecordProvenance,
};
use std::collections::{BTreeMap, BTreeSet};
use std::fmt;

/// Caller-supplied destination namespace table.
///
/// The table is keyed by the exact admitted source-set member key.  The
/// projection validates that it is total over observed members and contains
/// no unknown members before producing any output.
pub(crate) type SourceSetNamespaceTable = BTreeMap<SourceSetMemberKey, String>;

/// Failure while validating the destination namespace table.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum SourceSetNamespaceProjectionError {
    /// A destination namespace is not a restricted identifier.
    InvalidDestinationNamespace {
        /// Member whose destination was invalid.
        member: SourceSetMemberKey,
        /// Supplied invalid destination namespace.
        namespace: String,
    },
    /// The table contains a member key absent from the observed source set.
    UnknownMember {
        /// Unknown table key.
        member: SourceSetMemberKey,
    },
    /// An observed member has no table entry.
    MissingMember {
        /// Observed member without a destination namespace.
        member: SourceSetMemberKey,
    },
    /// The designated root may not be projected into another namespace.
    RootNamespaceMismatch {
        /// Root member key.
        member: SourceSetMemberKey,
        /// Original root namespace.
        original: String,
        /// Supplied destination namespace.
        destination: String,
    },
}

impl fmt::Display for SourceSetNamespaceProjectionError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidDestinationNamespace { member, namespace } => write!(
                formatter,
                "invalid destination namespace {namespace:?} for source-set member {member}"
            ),
            Self::UnknownMember { member } => {
                write!(formatter, "destination table names unknown member {member}")
            }
            Self::MissingMember { member } => write!(
                formatter,
                "destination table has no namespace for observed member {member}"
            ),
            Self::RootNamespaceMismatch {
                member,
                original,
                destination,
            } => write!(
                formatter,
                "root member {member} changes namespace from {original:?} to {destination:?}"
            ),
        }
    }
}

impl std::error::Error for SourceSetNamespaceProjectionError {}

/// One projected identity-bearing semantic address occurrence.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct SourceSetProjectedAddress {
    original: AddressKey,
    projected: AddressKey,
    provenance: SourceSetRecordProvenance,
}

impl SourceSetProjectedAddress {
    /// Original source-local address key.
    #[must_use]
    pub(crate) fn original(&self) -> &AddressKey {
        &self.original
    }

    /// Namespace-projected address key.
    #[must_use]
    pub(crate) fn projected(&self) -> &AddressKey {
        &self.projected
    }

    /// Original member/role provenance.
    #[must_use]
    pub(crate) fn provenance(&self) -> &SourceSetRecordProvenance {
        &self.provenance
    }
}

/// One projected owner-role occurrence, retaining its typed record kind.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct SourceSetProjectedOwnerRole {
    original: OwnerRoleKey,
    projected: OwnerRoleKey,
    kind: SourceSetOwnerRoleRecordKind,
    provenance: SourceSetRecordProvenance,
}

impl SourceSetProjectedOwnerRole {
    /// Original source-local owner-role key.
    #[must_use]
    pub(crate) fn original(&self) -> &OwnerRoleKey {
        &self.original
    }

    /// Namespace-projected owner-role key.
    #[must_use]
    pub(crate) fn projected(&self) -> &OwnerRoleKey {
        &self.projected
    }

    /// Typed source record kind retained separately from the owner-role key.
    #[must_use]
    pub(crate) const fn kind(&self) -> SourceSetOwnerRoleRecordKind {
        self.kind
    }

    /// Original member/role provenance.
    #[must_use]
    pub(crate) fn provenance(&self) -> &SourceSetRecordProvenance {
        &self.provenance
    }
}

/// One retained module declaration bookkeeping occurrence.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct SourceSetRetainedModuleDeclaration {
    original: ModuleDeclarationKey,
    retained: ModuleDeclarationKey,
    provenance: SourceSetRecordProvenance,
}

impl SourceSetRetainedModuleDeclaration {
    /// Original source-local module declaration key.
    #[must_use]
    pub(crate) fn original(&self) -> &ModuleDeclarationKey {
        &self.original
    }

    /// Unchanged module declaration key retained as companion bookkeeping.
    ///
    /// A declaration namespace identifies the declared module source.  It is
    /// therefore not replaced by the owning member's destination namespace.
    #[must_use]
    pub(crate) fn retained(&self) -> &ModuleDeclarationKey {
        &self.retained
    }

    /// Original member/role provenance.
    #[must_use]
    pub(crate) fn provenance(&self) -> &SourceSetRecordProvenance {
        &self.provenance
    }
}

/// Deterministic in-memory namespace projection and collision observation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct SourceSetNamespaceProjectionObservation {
    root: SourceSetMemberKey,
    destinations: BTreeMap<SourceSetMemberKey, String>,
    projected_namespace_owners: BTreeMap<String, BTreeSet<SourceSetMemberKey>>,
    projected_namespace_collisions: BTreeMap<String, BTreeSet<SourceSetMemberKey>>,
    addresses: Vec<SourceSetProjectedAddress>,
    address_index: BTreeMap<AddressKey, Vec<usize>>,
    address_collisions: BTreeSet<AddressKey>,
    owner_roles: Vec<SourceSetProjectedOwnerRole>,
    owner_role_index: BTreeMap<OwnerRoleKey, BTreeMap<SourceSetOwnerRoleRecordKind, Vec<usize>>>,
    module_declarations: Vec<SourceSetRetainedModuleDeclaration>,
    module_declaration_index: BTreeMap<ModuleDeclarationKey, Vec<usize>>,
    module_declaration_repetitions: BTreeSet<ModuleDeclarationKey>,
}

impl SourceSetNamespaceProjectionObservation {
    /// Designated root member key.
    #[must_use]
    pub(crate) fn root(&self) -> &SourceSetMemberKey {
        &self.root
    }

    /// Validated destination namespace for every observed member.
    #[must_use]
    pub(crate) fn destinations(&self) -> &BTreeMap<SourceSetMemberKey, String> {
        &self.destinations
    }

    /// Destination namespace to all owning members.
    #[must_use]
    pub(crate) fn projected_namespace_owners(
        &self,
    ) -> &BTreeMap<String, BTreeSet<SourceSetMemberKey>> {
        &self.projected_namespace_owners
    }

    /// Destination namespaces with more than one owning member.
    #[must_use]
    pub(crate) fn projected_namespace_collisions(
        &self,
    ) -> &BTreeMap<String, BTreeSet<SourceSetMemberKey>> {
        &self.projected_namespace_collisions
    }

    /// Every projected semantic address occurrence in stable member/key order.
    #[must_use]
    pub(crate) fn addresses(&self) -> &[SourceSetProjectedAddress] {
        &self.addresses
    }

    /// Number of projected semantic address occurrences.
    #[must_use]
    pub(crate) fn semantic_address_coverage_count(&self) -> usize {
        self.addresses.len()
    }

    /// Projected address index to coverage-record positions.
    #[must_use]
    pub(crate) fn address_index(&self) -> &BTreeMap<AddressKey, Vec<usize>> {
        &self.address_index
    }

    /// Projected full-address keys with multiple retained occurrences.
    #[must_use]
    pub(crate) fn address_collisions(&self) -> &BTreeSet<AddressKey> {
        &self.address_collisions
    }

    /// Every projected owner-role occurrence in stable member/key/kind order.
    #[must_use]
    pub(crate) fn owner_roles(&self) -> &[SourceSetProjectedOwnerRole] {
        &self.owner_roles
    }

    /// Projected owner-role index retaining record kind as a separate key.
    #[must_use]
    pub(crate) fn owner_role_index(
        &self,
    ) -> &BTreeMap<OwnerRoleKey, BTreeMap<SourceSetOwnerRoleRecordKind, Vec<usize>>> {
        &self.owner_role_index
    }

    /// Every projected module declaration bookkeeping occurrence.
    #[must_use]
    pub(crate) fn module_declarations(&self) -> &[SourceSetRetainedModuleDeclaration] {
        &self.module_declarations
    }

    /// Retained module declaration index to coverage-record positions.
    #[must_use]
    pub(crate) fn module_declaration_index(&self) -> &BTreeMap<ModuleDeclarationKey, Vec<usize>> {
        &self.module_declaration_index
    }

    /// Retained declaration keys with multiple legal bookkeeping occurrences.
    #[must_use]
    pub(crate) fn module_declaration_repetitions(&self) -> &BTreeSet<ModuleDeclarationKey> {
        &self.module_declaration_repetitions
    }
}

/// Observe an in-memory destination-namespace projection over existing
/// source-set provenance.
///
/// Validation is deterministic and fail-closed before any projection is
/// built: invalid destination identifiers, unknown table members, missing
/// observed members, and root namespace changes are reported in that order.
/// Collision evidence is retained in successful output and is not a verdict.
pub(crate) fn observe_source_set_namespace_projection(
    provenance: &SourceSetProvenanceObservation,
    destinations: &SourceSetNamespaceTable,
) -> Result<SourceSetNamespaceProjectionObservation, SourceSetNamespaceProjectionError> {
    validate_destinations(provenance, destinations)?;

    let mut projected_namespace_owners: BTreeMap<String, BTreeSet<SourceSetMemberKey>> =
        BTreeMap::new();
    for (member, destination) in destinations {
        projected_namespace_owners
            .entry(destination.clone())
            .or_default()
            .insert(member.clone());
    }
    let projected_namespace_collisions = projected_namespace_owners
        .iter()
        .filter(|(_, owners)| owners.len() > 1)
        .map(|(namespace, owners)| (namespace.clone(), owners.clone()))
        .collect();

    let mut addresses = Vec::new();
    let mut address_index: BTreeMap<AddressKey, Vec<usize>> = BTreeMap::new();
    let mut owner_roles = Vec::new();
    let mut owner_role_index: BTreeMap<
        OwnerRoleKey,
        BTreeMap<SourceSetOwnerRoleRecordKind, Vec<usize>>,
    > = BTreeMap::new();
    let mut module_declarations = Vec::new();
    let mut module_declaration_index: BTreeMap<ModuleDeclarationKey, Vec<usize>> = BTreeMap::new();

    for (member, inventory) in provenance.members() {
        let destination = destinations
            .get(member)
            .expect("destination validation makes the table total");

        for (original, provenance) in inventory.semantic_addresses() {
            let projected = project_address(original, destination);
            let position = addresses.len();
            addresses.push(SourceSetProjectedAddress {
                original: original.clone(),
                projected: projected.clone(),
                provenance: provenance.clone(),
            });
            address_index.entry(projected).or_default().push(position);
        }

        for (original, records) in inventory.owner_roles() {
            let projected = project_owner_role(original, destination);
            for (kind, provenance) in records {
                let position = owner_roles.len();
                owner_roles.push(SourceSetProjectedOwnerRole {
                    original: original.clone(),
                    projected: projected.clone(),
                    kind: *kind,
                    provenance: provenance.clone(),
                });
                owner_role_index
                    .entry(projected.clone())
                    .or_default()
                    .entry(*kind)
                    .or_default()
                    .push(position);
            }
        }

        for (original, provenance) in inventory.module_declarations() {
            // Module declarations are companion source bookkeeping, not
            // semantic addresses contributed by the owning member.  Retain
            // their declared source key unchanged; only its provenance is
            // carried through this namespace projection.
            let position = module_declarations.len();
            module_declarations.push(SourceSetRetainedModuleDeclaration {
                original: original.clone(),
                retained: original.clone(),
                provenance: provenance.clone(),
            });
            module_declaration_index
                .entry(original.clone())
                .or_default()
                .push(position);
        }
    }

    let address_collisions = address_index
        .iter()
        .filter(|(_, occurrences)| occurrences.len() > 1)
        .map(|(address, _)| address.clone())
        .collect();
    let module_declaration_repetitions = module_declaration_index
        .iter()
        .filter(|(_, occurrences)| occurrences.len() > 1)
        .map(|(declaration, _)| declaration.clone())
        .collect();

    Ok(SourceSetNamespaceProjectionObservation {
        root: provenance.root().clone(),
        destinations: destinations.clone(),
        projected_namespace_owners,
        projected_namespace_collisions,
        addresses,
        address_index,
        address_collisions,
        owner_roles,
        owner_role_index,
        module_declarations,
        module_declaration_index,
        module_declaration_repetitions,
    })
}

/// Alias using the operation-oriented projection name.
pub(crate) fn project_source_set_namespaces(
    provenance: &SourceSetProvenanceObservation,
    destinations: &SourceSetNamespaceTable,
) -> Result<SourceSetNamespaceProjectionObservation, SourceSetNamespaceProjectionError> {
    observe_source_set_namespace_projection(provenance, destinations)
}

fn validate_destinations(
    provenance: &SourceSetProvenanceObservation,
    destinations: &SourceSetNamespaceTable,
) -> Result<(), SourceSetNamespaceProjectionError> {
    for (member, destination) in destinations {
        if !is_identifier(destination) {
            return Err(
                SourceSetNamespaceProjectionError::InvalidDestinationNamespace {
                    member: member.clone(),
                    namespace: destination.clone(),
                },
            );
        }
    }
    for member in destinations.keys() {
        if !provenance.members().contains_key(member) {
            return Err(SourceSetNamespaceProjectionError::UnknownMember {
                member: member.clone(),
            });
        }
    }
    for member in provenance.members().keys() {
        if !destinations.contains_key(member) {
            return Err(SourceSetNamespaceProjectionError::MissingMember {
                member: member.clone(),
            });
        }
    }

    let root = provenance.root();
    let destination = destinations
        .get(root)
        .expect("destination validation makes the table total");
    if destination != root.namespace() {
        return Err(SourceSetNamespaceProjectionError::RootNamespaceMismatch {
            member: root.clone(),
            original: root.namespace().to_owned(),
            destination: destination.clone(),
        });
    }
    Ok(())
}

fn project_address(original: &AddressKey, destination: &str) -> AddressKey {
    AddressKey::from_wire(&Address {
        namespace: destination.to_owned(),
        anchors: original.anchors().to_vec(),
        kind: original.kind().clone(),
        role: original.role().to_owned(),
    })
    .expect("validated destination and existing address components form a valid key")
}

fn project_owner_role(original: &OwnerRoleKey, destination: &str) -> OwnerRoleKey {
    let owner = project_address(original.owner(), destination);
    OwnerRoleKey::from_wire(
        &Address {
            namespace: owner.namespace().to_owned(),
            anchors: owner.anchors().to_vec(),
            kind: owner.kind().clone(),
            role: owner.role().to_owned(),
        },
        original.role(),
    )
    .expect("validated destination and existing owner-role components form a valid key")
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::body_document::ResourceProfile;
    use crate::restricted_source_set_handoff::{
        RestrictedSourceSetHandoff, build_restricted_source_set_handoff,
    };
    use crate::source_set_preparation::SourceSetInput;
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

    fn source_with_owner_roles(document: &str, namespace: &str) -> Vec<u8> {
        let mut value: Value =
            serde_json::from_slice(&source(document, namespace)).expect("source is valid JSON");
        let owner = value["body"]["parts"][0]["address"].clone();
        let transform = serde_json::json!({
            "translation": [0, 0, 0],
            "rotation_xyzw": [0, 0, 0, 1]
        });
        value["body"]["frames"] = serde_json::json!([{
            "owner": owner.clone(),
            "role": "shared_role",
            "transform": transform
        }]);
        value["body"]["landmarks"] = serde_json::json!([{
            "owner": owner.clone(),
            "role": "shared_role",
            "frame": {
                "owner": owner.clone(),
                "role": "shared_role"
            },
            "position": [0, 0, 0]
        }]);
        value["body"]["dimensions"] = serde_json::json!([{
            "owner": owner,
            "role": "shared_role",
            "value": 1
        }]);
        value["body"]["fields"] = serde_json::json!([{
            "address": {
                "namespace": namespace,
                "anchors": ["field"],
                "kind": "field",
                "role": "measurement"
            },
            "owner": value["body"]["parts"][0]["address"].clone(),
            "frame": {
                "owner": value["body"]["parts"][0]["address"].clone(),
                "role": "shared_role"
            },
            "channel": "measurement"
        }]);
        serde_json::to_vec(&value).expect("source serializes")
    }

    fn source_with_module_namespace(
        document: &str,
        namespace: &str,
        module_namespace: &str,
    ) -> Vec<u8> {
        let mut value: Value =
            serde_json::from_slice(&source(document, namespace)).expect("source is valid JSON");
        value["body"]["modules"][0]["declaration"]["namespace"] =
            Value::String(module_namespace.to_owned());
        serde_json::to_vec(&value).expect("source serializes")
    }

    fn source_with_module_declaration(
        document: &str,
        namespace: &str,
        module_document: &str,
        module_namespace: &str,
    ) -> Vec<u8> {
        let mut value: Value =
            serde_json::from_slice(&source(document, namespace)).expect("source is valid JSON");
        value["body"]["modules"][0]["declaration"]["document"] =
            Value::String(module_document.to_owned());
        value["body"]["modules"][0]["declaration"]["namespace"] =
            Value::String(module_namespace.to_owned());
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

    fn declaration(document: &str, namespace: &str) -> Value {
        serde_json::json!({
            "document": document,
            "namespace": namespace,
            "content_sha256": format!("sha256:{}", "a".repeat(64)),
        })
    }

    fn with_dependencies(source: &[u8], dependencies: Value) -> Vec<u8> {
        let mut value: Value = serde_json::from_slice(source).expect("source is valid JSON");
        value["source"]["dependencies"] = dependencies;
        serde_json::to_vec(&value).expect("source serializes")
    }

    fn handoff<'a>(root: &'a [u8], dependencies: Vec<&'a [u8]>) -> RestrictedSourceSetHandoff {
        build_restricted_source_set_handoff(crate::source_set_preparation::prepare_source_set(
            SourceSetInput::new(root, dependencies, ResourceProfile::ORDINARY),
        ))
        .expect("source-set handoff succeeds")
    }

    fn identity_table(provenance: &SourceSetProvenanceObservation) -> SourceSetNamespaceTable {
        provenance
            .members()
            .keys()
            .map(|member| (member.clone(), member.namespace().to_owned()))
            .collect()
    }

    fn observed_members(
        provenance: &SourceSetProvenanceObservation,
    ) -> BTreeSet<SourceSetMemberKey> {
        provenance.members().keys().cloned().collect()
    }

    fn assert_index_positions_are_sound(
        projection: &SourceSetNamespaceProjectionObservation,
        observed_members: &BTreeSet<SourceSetMemberKey>,
    ) {
        for (projected, positions) in projection.address_index() {
            for position in positions {
                let record = projection
                    .addresses()
                    .get(*position)
                    .expect("address index position is in bounds");
                assert_eq!(record.projected(), projected);
                assert!(observed_members.contains(record.provenance().member()));
            }
        }

        for (projected, by_kind) in projection.owner_role_index() {
            for (kind, positions) in by_kind {
                for position in positions {
                    let record = projection
                        .owner_roles()
                        .get(*position)
                        .expect("owner-role index position is in bounds");
                    assert_eq!(record.projected(), projected);
                    assert_eq!(record.kind(), *kind);
                    assert!(observed_members.contains(record.provenance().member()));
                }
            }
        }

        for (retained, positions) in projection.module_declaration_index() {
            for position in positions {
                let record = projection
                    .module_declarations()
                    .get(*position)
                    .expect("module declaration index position is in bounds");
                assert_eq!(record.retained(), retained);
                assert!(observed_members.contains(record.provenance().member()));
            }
        }
    }

    #[test]
    fn identity_table_projects_every_address_once_without_false_collision() {
        let root = source("root_doc", "root_ns");
        let dependency =
            source_with_module_namespace("dependency_doc", "dependency_ns", "declared_module_ns");
        let prepared = handoff(&root, vec![&dependency]);
        let provenance = observe_source_set_provenance(&prepared);
        let destinations = identity_table(&provenance);
        let projection = observe_source_set_namespace_projection(&provenance, &destinations)
            .expect("identity projection succeeds");
        assert_index_positions_are_sound(&projection, &observed_members(&provenance));

        let expected_count: usize = provenance
            .members()
            .values()
            .map(|member| member.semantic_addresses().len())
            .sum();
        assert_eq!(projection.semantic_address_coverage_count(), expected_count);
        assert_eq!(
            projection.addresses().len(),
            projection
                .address_index()
                .values()
                .map(Vec::len)
                .sum::<usize>()
        );
        assert!(projection.address_collisions().is_empty());
        assert!(projection.projected_namespace_collisions().is_empty());
        assert!(projection.addresses().iter().all(|record| {
            record.original().namespace() == record.projected().namespace()
                && destinations.contains_key(record.provenance().member())
                && destinations[record.provenance().member()] == record.projected().namespace()
        }));
    }

    #[test]
    fn dependency_namespace_change_preserves_components_and_root_change_fails() {
        let root = source("root_doc", "root_ns");
        let dependency =
            source_with_module_namespace("dependency_doc", "dependency_ns", "declared_module_ns");
        let prepared = handoff(&root, vec![&dependency]);
        let provenance = observe_source_set_provenance(&prepared);
        let dependency_key = provenance
            .members()
            .keys()
            .find(|member| member.document() == "dependency_doc")
            .expect("dependency member exists")
            .clone();
        let mut destinations = identity_table(&provenance);
        destinations.insert(dependency_key.clone(), "merged_ns".into());
        let projection = observe_source_set_namespace_projection(&provenance, &destinations)
            .expect("dependency projection succeeds");
        let dependency_role = provenance
            .members()
            .get(&dependency_key)
            .expect("dependency inventory exists")
            .role();

        assert!(
            projection
                .addresses()
                .iter()
                .filter(|record| { record.provenance().member() == &dependency_key })
                .all(|record| {
                    record.projected().namespace() == "merged_ns"
                        && record.original().anchors() == record.projected().anchors()
                        && record.original().kind() == record.projected().kind()
                        && record.original().role() == record.projected().role()
                        && record.provenance().role() == dependency_role
                })
        );
        assert!(
            projection
                .module_declarations()
                .iter()
                .filter(|record| record.provenance().member() == &dependency_key)
                .all(|record| {
                    record.original() == record.retained()
                        && record.retained().namespace() == "declared_module_ns"
                })
        );

        let root_key = provenance.root().clone();
        destinations.insert(root_key.clone(), "changed_root".into());
        assert!(matches!(
            observe_source_set_namespace_projection(&provenance, &destinations),
            Err(SourceSetNamespaceProjectionError::RootNamespaceMismatch { member, .. })
                if member == root_key
        ));
    }

    #[test]
    fn missing_unknown_and_invalid_tables_fail_deterministically_without_output() {
        let root = source("root_doc", "root_ns");
        let dependency = source("dependency_doc", "dependency_ns");
        let prepared = handoff(&root, vec![&dependency]);
        let provenance = observe_source_set_provenance(&prepared);

        let mut missing = identity_table(&provenance);
        let missing_key = provenance
            .members()
            .keys()
            .find(|member| member.document() == "dependency_doc")
            .expect("dependency member exists")
            .clone();
        missing.remove(&missing_key);
        assert!(matches!(
            observe_source_set_namespace_projection(&provenance, &missing),
            Err(SourceSetNamespaceProjectionError::MissingMember { member }) if member == missing_key
        ));

        let unknown_source = source("unknown_doc", "unknown_ns");
        let unknown_prepared = handoff(&unknown_source, Vec::new());
        let unknown_provenance = observe_source_set_provenance(&unknown_prepared);
        let unknown_key = unknown_provenance
            .members()
            .keys()
            .next()
            .expect("unknown key exists")
            .clone();
        let mut unknown = identity_table(&provenance);
        unknown.insert(unknown_key.clone(), "unknown_ns".into());
        assert!(matches!(
            observe_source_set_namespace_projection(&provenance, &unknown),
            Err(SourceSetNamespaceProjectionError::UnknownMember { member }) if member == unknown_key
        ));

        let mut invalid = identity_table(&provenance);
        let invalid_key = invalid.keys().next().expect("member exists").clone();
        invalid.insert(invalid_key.clone(), "Bad Namespace".into());
        assert!(matches!(
            observe_source_set_namespace_projection(&provenance, &invalid),
            Err(SourceSetNamespaceProjectionError::InvalidDestinationNamespace { member, namespace })
                if member == invalid_key && namespace == "Bad Namespace"
        ));
    }

    #[test]
    fn combined_table_faults_follow_invalid_unknown_missing_root_precedence() {
        let root = source("root_doc", "root_ns");
        let dependency = source("dependency_doc", "dependency_ns");
        let prepared = handoff(&root, vec![&dependency]);
        let provenance = observe_source_set_provenance(&prepared);
        let dependency_key = provenance
            .members()
            .keys()
            .find(|member| member.document() == "dependency_doc")
            .expect("dependency member exists")
            .clone();
        let unknown_source = source("unknown_doc", "unknown_ns");
        let unknown_prepared = handoff(&unknown_source, Vec::new());
        let unknown_provenance = observe_source_set_provenance(&unknown_prepared);
        let unknown_key = unknown_provenance
            .members()
            .keys()
            .next()
            .expect("unknown member exists")
            .clone();

        let mut destinations = identity_table(&provenance);
        destinations.insert(provenance.root().clone(), "Bad Namespace".into());
        destinations.insert(unknown_key.clone(), "unknown_ns".into());
        destinations.remove(&dependency_key);
        assert!(matches!(
            observe_source_set_namespace_projection(&provenance, &destinations),
            Err(SourceSetNamespaceProjectionError::InvalidDestinationNamespace { .. })
        ));

        destinations.insert(provenance.root().clone(), "root_ns".into());
        assert!(matches!(
            observe_source_set_namespace_projection(&provenance, &destinations),
            Err(SourceSetNamespaceProjectionError::UnknownMember { member })
                if member == unknown_key
        ));

        destinations.remove(&unknown_key);
        assert!(matches!(
            observe_source_set_namespace_projection(&provenance, &destinations),
            Err(SourceSetNamespaceProjectionError::MissingMember { member })
                if member == dependency_key
        ));

        destinations.insert(dependency_key.clone(), "dependency_ns".into());
        assert!(observe_source_set_namespace_projection(&provenance, &destinations).is_ok());

        destinations.insert(provenance.root().clone(), "changed_root".into());
        assert!(matches!(
            observe_source_set_namespace_projection(&provenance, &destinations),
            Err(SourceSetNamespaceProjectionError::RootNamespaceMismatch { member, .. })
                if &member == provenance.root()
        ));
    }

    #[test]
    fn projected_namespace_and_full_key_collisions_preserve_all_occurrences() {
        let root = source("root_doc", "root_ns");
        let first = source("first_dep", "first_ns");
        let second = source("second_dep", "second_ns");
        let prepared = handoff(&root, vec![&second, &first]);
        let provenance = observe_source_set_provenance(&prepared);
        let mut destinations = identity_table(&provenance);
        for member in destinations.keys().cloned().collect::<Vec<_>>() {
            if member.document() != "root_doc" {
                destinations.insert(member, "merged_ns".into());
            }
        }
        let projection = observe_source_set_namespace_projection(&provenance, &destinations)
            .expect("collision projection succeeds");
        assert_index_positions_are_sound(&projection, &observed_members(&provenance));

        assert_eq!(
            projection.projected_namespace_collisions()["merged_ns"].len(),
            2
        );
        assert!(!projection.address_collisions().is_empty());
        assert!(
            projection
                .address_collisions()
                .iter()
                .all(|address| { projection.address_index()[address].len() > 1 })
        );
        assert!(projection.module_declaration_repetitions().is_empty());
        assert!(
            projection
                .module_declarations()
                .iter()
                .all(|record| record.original() == record.retained())
        );
        assert_eq!(
            projection
                .addresses()
                .iter()
                .filter(|record| record.projected().namespace() == "merged_ns")
                .count(),
            2 * source_address_count()
        );
    }

    fn source_address_count() -> usize {
        let root = source("count_doc", "count_ns");
        let prepared = handoff(&root, Vec::new());
        observe_source_set_provenance(&prepared)
            .members()
            .values()
            .map(|member| member.semantic_addresses().len())
            .sum()
    }

    #[test]
    fn owner_role_kinds_and_module_declarations_remain_separate() {
        let root = source_with_owner_roles("owner_doc", "owner_ns");
        let prepared = handoff(&root, Vec::new());
        let provenance = observe_source_set_provenance(&prepared);
        let projection =
            observe_source_set_namespace_projection(&provenance, &identity_table(&provenance))
                .expect("owner-role projection succeeds");
        assert_index_positions_are_sound(&projection, &observed_members(&provenance));

        let shared = projection
            .owner_roles()
            .iter()
            .filter(|record| record.original().role() == "shared_role")
            .collect::<Vec<_>>();
        assert_eq!(shared.len(), 3);
        assert_eq!(
            shared
                .iter()
                .map(|record| record.kind())
                .collect::<BTreeSet<_>>(),
            BTreeSet::from([
                SourceSetOwnerRoleRecordKind::Dimension,
                SourceSetOwnerRoleRecordKind::Frame,
                SourceSetOwnerRoleRecordKind::Landmark,
            ])
        );
        assert_eq!(projection.module_declarations().len(), 1);
        assert_eq!(
            projection
                .module_declaration_index()
                .values()
                .map(Vec::len)
                .sum::<usize>(),
            1
        );
        let expected_owner_roles: usize = provenance
            .members()
            .values()
            .map(|member| {
                member
                    .owner_roles()
                    .values()
                    .map(BTreeMap::len)
                    .sum::<usize>()
            })
            .sum();
        let expected_module_declarations: usize = provenance
            .members()
            .values()
            .map(|member| member.module_declarations().len())
            .sum();
        assert_eq!(projection.owner_roles().len(), expected_owner_roles);
        assert_eq!(
            projection.module_declarations().len(),
            expected_module_declarations
        );
    }

    #[test]
    fn owner_role_projection_retains_colliding_dependencies_by_kind_and_provenance() {
        let root = source("root_doc", "root_ns");
        let first = source_with_owner_roles("first_dep", "first_ns");
        let second = source_with_owner_roles("second_dep", "second_ns");
        let prepared = handoff(&root, vec![&second, &first]);
        let provenance = observe_source_set_provenance(&prepared);
        let mut destinations = identity_table(&provenance);
        for member in destinations.keys().cloned().collect::<Vec<_>>() {
            if member.document() != "root_doc" {
                destinations.insert(member, "merged_ns".into());
            }
        }
        let projection = observe_source_set_namespace_projection(&provenance, &destinations)
            .expect("owner-role collision projection succeeds");
        assert_index_positions_are_sound(&projection, &observed_members(&provenance));

        let dependency_members: BTreeSet<_> = provenance
            .members()
            .keys()
            .filter(|member| member.document().ends_with("_dep"))
            .cloned()
            .collect();
        let candidates: Vec<_> = projection
            .owner_role_index()
            .iter()
            .filter(|(owner_role, by_kind)| {
                owner_role.owner().namespace() == "merged_ns"
                    && owner_role.role() == "shared_role"
                    && by_kind.len() == 3
            })
            .collect();
        assert_eq!(candidates.len(), 1);
        let (projected, by_kind) = candidates[0];
        assert_eq!(
            by_kind.keys().copied().collect::<BTreeSet<_>>(),
            BTreeSet::from([
                SourceSetOwnerRoleRecordKind::Dimension,
                SourceSetOwnerRoleRecordKind::Frame,
                SourceSetOwnerRoleRecordKind::Landmark,
            ])
        );
        for (kind, positions) in by_kind {
            assert_eq!(positions.len(), dependency_members.len());
            for position in positions {
                let record = projection
                    .owner_roles()
                    .get(*position)
                    .expect("owner-role collision position is in bounds");
                assert_eq!(record.projected(), projected);
                assert_eq!(record.kind(), *kind);
                assert!(dependency_members.contains(record.provenance().member()));
            }
        }
    }

    #[test]
    fn repeated_module_declarations_remain_separate_from_address_evidence() {
        let root = source("root_doc", "root_ns");
        let first =
            source_with_module_declaration("first_dep", "first_ns", "shared_module", "declared_ns");
        let second = source_with_module_declaration(
            "second_dep",
            "second_ns",
            "shared_module",
            "declared_ns",
        );
        let prepared = handoff(&root, vec![&first, &second]);
        let provenance = observe_source_set_provenance(&prepared);
        let mut destinations = identity_table(&provenance);
        for member in destinations.keys().cloned().collect::<Vec<_>>() {
            if member.document() != "root_doc" {
                destinations.insert(member, "merged_ns".into());
            }
        }
        let projection = observe_source_set_namespace_projection(&provenance, &destinations)
            .expect("projection succeeds");
        assert_index_positions_are_sound(&projection, &observed_members(&provenance));

        assert!(!projection.module_declaration_repetitions().is_empty());
        assert!(
            projection
                .module_declaration_repetitions()
                .iter()
                .all(|declaration| declaration.namespace() == "declared_ns")
        );
        assert!(
            projection
                .module_declarations()
                .iter()
                .filter(|record| record.retained().document() == "shared_module")
                .all(|record| {
                    record.original() == record.retained()
                        && record.retained().namespace() == "declared_ns"
                })
        );
        assert!(!projection.address_collisions().is_empty());
    }

    #[test]
    fn member_and_source_collection_permutations_have_equal_projection() {
        let root = with_dependencies(
            &source("root_doc", "root_ns"),
            serde_json::json!([declaration("dep_a", "a_ns"), declaration("dep_b", "b_ns")]),
        );
        let dep_a = source("dep_a", "a_ns");
        let dep_b = source("dep_b", "b_ns");
        let first_prepared = handoff(&root, vec![&dep_a, &dep_b]);
        let second_prepared = handoff(&root, vec![&dep_b, &dep_a]);
        let first_provenance = observe_source_set_provenance(&first_prepared);
        let second_provenance = observe_source_set_provenance(&second_prepared);
        assert_eq!(
            observe_source_set_namespace_projection(
                &first_provenance,
                &identity_table(&first_provenance)
            ),
            observe_source_set_namespace_projection(
                &second_provenance,
                &identity_table(&second_provenance)
            )
        );

        let root_with_dependency = with_dependencies(
            &source("root_doc", "root_ns"),
            serde_json::json!([declaration("rich_dep", "rich_ns")]),
        );
        let rich_source = source_with_owner_roles("rich_dep", "rich_ns");
        let original: Value =
            serde_json::from_slice(&rich_source).expect("rich source is valid JSON");
        let mut permuted = original.clone();
        for collection in [
            "modules",
            "parts",
            "joints",
            "sockets",
            "attachments",
            "landmarks",
            "dimensions",
            "frames",
            "regions",
            "capabilities",
            "fields",
        ] {
            permuted["body"][collection]
                .as_array_mut()
                .expect("body collection exists")
                .reverse();
        }
        let original = serde_json::to_vec(&original).expect("source serializes");
        let permuted = serde_json::to_vec(&permuted).expect("source serializes");
        let first_prepared = handoff(&root_with_dependency, vec![&original]);
        let second_prepared = handoff(&root_with_dependency, vec![&permuted]);
        let first_provenance = observe_source_set_provenance(&first_prepared);
        let second_provenance = observe_source_set_provenance(&second_prepared);
        let mut first_destinations = identity_table(&first_provenance);
        let mut second_destinations = identity_table(&second_provenance);
        let first_rich_member = first_provenance
            .members()
            .keys()
            .find(|member| member.document() == "rich_dep")
            .expect("rich member exists")
            .clone();
        let second_rich_member = second_provenance
            .members()
            .keys()
            .find(|member| member.document() == "rich_dep")
            .expect("rich member exists")
            .clone();
        first_destinations.insert(first_rich_member.clone(), "merged_ns".into());
        second_destinations.insert(second_rich_member.clone(), "merged_ns".into());
        let first_projection =
            observe_source_set_namespace_projection(&first_provenance, &first_destinations)
                .expect("rich projection succeeds");
        let second_projection =
            observe_source_set_namespace_projection(&second_provenance, &second_destinations)
                .expect("permuted rich projection succeeds");
        assert_eq!(first_projection, second_projection);
        assert_index_positions_are_sound(&first_projection, &observed_members(&first_provenance));
        let rich_addresses: Vec<_> = first_projection
            .addresses()
            .iter()
            .filter(|record| record.provenance().member() == &first_rich_member)
            .collect();
        let expected_rich_count = first_provenance
            .members()
            .get(&first_rich_member)
            .expect("rich inventory exists")
            .semantic_addresses()
            .len();
        assert_eq!(rich_addresses.len(), expected_rich_count);
        assert_eq!(
            rich_addresses
                .iter()
                .map(|record| crate::semantic_address::kind_name(record.projected().kind()))
                .collect::<BTreeSet<_>>(),
            BTreeSet::from([
                "attachment",
                "capability",
                "field",
                "joint",
                "part",
                "region",
                "socket",
            ])
        );
        assert!(rich_addresses.iter().all(|record| {
            record.projected().namespace() == "merged_ns"
                && record.original().anchors() == record.projected().anchors()
                && record.original().kind() == record.projected().kind()
                && record.original().role() == record.projected().role()
        }));
    }
}
