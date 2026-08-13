//! Provisional deterministic structural body-graph/index.
//!
//! This is an inspectable index over an already admitted [`BodyDocument`].  It
//! is intentionally not a finalized Readiness 3 resolved snapshot: values are
//! retained in their source representation, no canonical bytes/digest are
//! produced, and no numeric or frame semantics are applied.

use crate::body_document::{
    Attachment, Basis, BodyDocument, Capability, Contract, Dimension, Extension, Field, Frame,
    Joint, Landmark, Module, Part, Profiles, Region, Socket, Source,
};
use crate::semantic_address::{AddressKey, AddressKeyError, is_identifier};
use std::cmp::Ordering;
use std::collections::BTreeMap;
use std::fmt;
use std::hash::{Hash, Hasher};

/// Stable key for a module declaration, which is source-scope identity rather
/// than an additional embodied address kind.
#[derive(Clone, Debug, Eq, PartialEq, Ord, PartialOrd, Hash)]
pub struct ModuleDeclarationKey {
    document: String,
    namespace: String,
    anchors: Vec<String>,
    role: String,
}

impl ModuleDeclarationKey {
    /// Checked construction from a wire module declaration.
    pub fn from_declaration(
        declaration: &crate::body_document::Declaration,
    ) -> Result<Self, ModuleDeclarationKeyError> {
        for (component, value) in [
            (
                ModuleDeclarationComponent::Document,
                declaration.document.as_str(),
            ),
            (
                ModuleDeclarationComponent::Namespace,
                declaration.namespace.as_str(),
            ),
            (ModuleDeclarationComponent::Role, declaration.role.as_str()),
        ] {
            if !is_identifier(value) {
                return Err(ModuleDeclarationKeyError::InvalidComponent {
                    component,
                    value: value.to_owned(),
                });
            }
        }
        for anchor in &declaration.anchors {
            if !is_identifier(anchor) {
                return Err(ModuleDeclarationKeyError::InvalidComponent {
                    component: ModuleDeclarationComponent::Anchor,
                    value: anchor.clone(),
                });
            }
        }
        Ok(Self {
            document: declaration.document.clone(),
            namespace: declaration.namespace.clone(),
            anchors: declaration.anchors.clone(),
            role: declaration.role.clone(),
        })
    }

    /// Source-document identity of the declaration.
    #[must_use]
    pub fn document(&self) -> &str {
        &self.document
    }

    /// Source namespace of the declaration.
    #[must_use]
    pub fn namespace(&self) -> &str {
        &self.namespace
    }

    /// Ordered module-instance anchors.
    #[must_use]
    pub fn anchors(&self) -> &[String] {
        &self.anchors
    }

    /// Declaration role.
    #[must_use]
    pub fn role(&self) -> &str {
        &self.role
    }
}

impl TryFrom<&crate::body_document::Declaration> for ModuleDeclarationKey {
    type Error = ModuleDeclarationKeyError;

    fn try_from(value: &crate::body_document::Declaration) -> Result<Self, Self::Error> {
        Self::from_declaration(value)
    }
}

/// Declaration component that failed the restricted identifier profile.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub enum ModuleDeclarationComponent {
    Document,
    Namespace,
    Anchor,
    Role,
}

/// Module declaration key construction failure.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum ModuleDeclarationKeyError {
    InvalidComponent {
        component: ModuleDeclarationComponent,
        value: String,
    },
}

impl fmt::Display for ModuleDeclarationKeyError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidComponent { component, value } => {
                write!(formatter, "invalid {component:?} identifier {value:?}")
            }
        }
    }
}

impl std::error::Error for ModuleDeclarationKeyError {}

/// Failure while constructing the provisional sorted index.
///
/// This is deliberately narrower than semantic validation: it reports only
/// failures that would make a deterministic keyed index impossible.  It does
/// not claim to validate containment, references, attachments, or numeric
/// semantics.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum StructuralGraphIndexError {
    /// An identity-bearing record had an invalid structural address.
    InvalidAddress {
        collection: &'static str,
        error: AddressKeyError,
    },
    /// Two identity-bearing records would occupy one keyed slot.
    DuplicateAddress { address: AddressKey },
    /// A module declaration could not form its deterministic key.
    InvalidModuleDeclaration { error: ModuleDeclarationKeyError },
    /// Two module declarations would occupy one keyed slot.
    DuplicateModuleDeclaration { key: ModuleDeclarationKey },
    /// An owner/role record could not form its deterministic key.
    InvalidOwnerRole {
        collection: &'static str,
        error: OwnerRoleKeyError,
    },
    /// Two owner/role records would occupy one keyed slot.
    DuplicateOwnerRole {
        collection: &'static str,
        key: OwnerRoleKey,
    },
}

impl fmt::Display for StructuralGraphIndexError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidAddress { collection, error } => {
                write!(formatter, "invalid {collection} address: {error}")
            }
            Self::DuplicateAddress { address } => {
                write!(
                    formatter,
                    "duplicate address in structural index: {address:?}"
                )
            }
            Self::InvalidModuleDeclaration { error } => {
                write!(formatter, "invalid module declaration: {error}")
            }
            Self::DuplicateModuleDeclaration { key } => {
                write!(formatter, "duplicate module declaration: {key:?}")
            }
            Self::InvalidOwnerRole { collection, error } => {
                write!(formatter, "invalid {collection} owner/role: {error}")
            }
            Self::DuplicateOwnerRole { collection, key } => {
                write!(formatter, "duplicate {collection} owner/role: {key:?}")
            }
        }
    }
}

impl std::error::Error for StructuralGraphIndexError {}

/// Stable owner/role key for non-addressed source records.
#[derive(Clone, Debug)]
pub struct OwnerRoleKey {
    owner: AddressKey,
    role: String,
}

/// Failure while constructing an owner/role key from wire fields.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum OwnerRoleKeyError {
    /// The owner address failed restricted-address validation.
    InvalidOwner(AddressKeyError),
    /// The role failed restricted-identifier validation.
    InvalidRole { value: String },
}

impl fmt::Display for OwnerRoleKeyError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidOwner(error) => write!(formatter, "invalid owner address: {error}"),
            Self::InvalidRole { value } => write!(formatter, "invalid owner role {value:?}"),
        }
    }
}

impl std::error::Error for OwnerRoleKeyError {}

impl OwnerRoleKey {
    /// Checked construction from a wire owner address and role.
    pub fn from_wire(
        owner: &crate::body_document::Address,
        role: &str,
    ) -> Result<Self, OwnerRoleKeyError> {
        if !is_identifier(role) {
            return Err(OwnerRoleKeyError::InvalidRole {
                value: role.to_owned(),
            });
        }
        Ok(Self {
            owner: AddressKey::try_from(owner).map_err(OwnerRoleKeyError::InvalidOwner)?,
            role: role.to_owned(),
        })
    }

    /// Owner address key.
    #[must_use]
    pub fn owner(&self) -> &AddressKey {
        &self.owner
    }

    /// Owner-local role.
    #[must_use]
    pub fn role(&self) -> &str {
        &self.role
    }
}

impl PartialEq for OwnerRoleKey {
    fn eq(&self, other: &Self) -> bool {
        self.owner == other.owner && self.role == other.role
    }
}
impl Eq for OwnerRoleKey {}
impl Hash for OwnerRoleKey {
    fn hash<H: Hasher>(&self, state: &mut H) {
        self.owner.hash(state);
        self.role.hash(state);
    }
}
impl Ord for OwnerRoleKey {
    fn cmp(&self, other: &Self) -> Ordering {
        self.owner
            .cmp(&other.owner)
            .then_with(|| self.role.cmp(&other.role))
    }
}
impl PartialOrd for OwnerRoleKey {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

/// The deterministic provisional index produced after structural validation.
#[derive(Clone, Debug, PartialEq)]
pub struct StructuralBodyGraph {
    /// Original source identity and dependency declarations.
    source: Source,
    /// Original source basis.  No conversion is performed here.
    basis: Basis,
    /// The admitted profile declaration, retained for provenance only.
    profiles: Profiles,
    /// Original contract discriminator, retained for provenance only.
    contract: Contract,
    /// Opaque optional extensions retained without interpreting them.
    extensions: Vec<Extension>,
    /// Sorted module declarations, including absent optional declarations.
    modules: BTreeMap<ModuleDeclarationKey, Module>,
    /// Sorted identity-bearing collections.
    parts: BTreeMap<AddressKey, Part>,
    joints: BTreeMap<AddressKey, Joint>,
    sockets: BTreeMap<AddressKey, Socket>,
    attachments: BTreeMap<AddressKey, Attachment>,
    regions: BTreeMap<AddressKey, Region>,
    capabilities: BTreeMap<AddressKey, Capability>,
    fields: BTreeMap<AddressKey, Field>,
    /// Sorted owner/role collections retain source records and provenance.
    landmarks: BTreeMap<OwnerRoleKey, Landmark>,
    dimensions: BTreeMap<OwnerRoleKey, Dimension>,
    frames: BTreeMap<OwnerRoleKey, Frame>,
}

impl StructuralBodyGraph {
    /// Build a deterministic provisional index from an already admitted body
    /// document.
    ///
    /// This operation preserves source records and provenance while sorting
    /// them by typed keys.  It is not a parser, schema validator, semantic
    /// resolver, or finalized Readiness 3 snapshot.  In particular it does not
    /// check graph topology, reference existence, dependency acquisition,
    /// transforms, numeric values, canonical bytes, or digests.
    pub(crate) fn from_admitted(
        document: &BodyDocument,
    ) -> Result<Self, StructuralGraphIndexError> {
        let mut graph = Self {
            source: document.source.clone(),
            basis: document.basis.clone(),
            profiles: document.profiles.clone(),
            contract: document.contract.clone(),
            extensions: document.extensions.clone(),
            modules: std::collections::BTreeMap::new(),
            parts: std::collections::BTreeMap::new(),
            joints: std::collections::BTreeMap::new(),
            sockets: std::collections::BTreeMap::new(),
            attachments: std::collections::BTreeMap::new(),
            regions: std::collections::BTreeMap::new(),
            capabilities: std::collections::BTreeMap::new(),
            fields: std::collections::BTreeMap::new(),
            landmarks: std::collections::BTreeMap::new(),
            dimensions: std::collections::BTreeMap::new(),
            frames: std::collections::BTreeMap::new(),
        };

        for module in &document.body.modules {
            let key = ModuleDeclarationKey::from_declaration(&module.declaration)
                .map_err(|error| StructuralGraphIndexError::InvalidModuleDeclaration { error })?;
            if graph.modules.insert(key.clone(), module.clone()).is_some() {
                return Err(StructuralGraphIndexError::DuplicateModuleDeclaration { key });
            }
        }
        for record in &document.body.parts {
            insert_address_record(&mut graph.parts, &record.address, record, "parts")?;
        }
        for record in &document.body.joints {
            insert_address_record(&mut graph.joints, &record.address, record, "joints")?;
        }
        for record in &document.body.sockets {
            insert_address_record(&mut graph.sockets, &record.address, record, "sockets")?;
        }
        for record in &document.body.attachments {
            insert_address_record(
                &mut graph.attachments,
                &record.address,
                record,
                "attachments",
            )?;
        }
        for record in &document.body.regions {
            insert_address_record(&mut graph.regions, &record.address, record, "regions")?;
        }
        for record in &document.body.capabilities {
            insert_address_record(
                &mut graph.capabilities,
                &record.address,
                record,
                "capabilities",
            )?;
        }
        for record in &document.body.fields {
            insert_address_record(&mut graph.fields, &record.address, record, "fields")?;
        }
        for record in &document.body.landmarks {
            insert_owner_role_record(
                &mut graph.landmarks,
                &record.owner,
                &record.role,
                record,
                "landmarks",
            )?;
        }
        for record in &document.body.dimensions {
            insert_owner_role_record(
                &mut graph.dimensions,
                &record.owner,
                &record.role,
                record,
                "dimensions",
            )?;
        }
        for record in &document.body.frames {
            insert_owner_role_record(
                &mut graph.frames,
                &record.owner,
                &record.role,
                record,
                "frames",
            )?;
        }
        Ok(graph)
    }

    /// Assemble a graph from a document known to have passed structural
    /// validation.  This method is crate-visible so callers cannot mistake it
    /// for a validating or finalized resolver operation.
    pub(crate) fn from_validated(document: &BodyDocument) -> Self {
        Self::from_admitted(document).expect("structural validation must precede graph indexing")
    }

    /// Original source identity and dependency declarations.
    #[must_use]
    pub fn source(&self) -> &Source {
        &self.source
    }

    /// Original source basis, without numeric conversion.
    #[must_use]
    pub fn basis(&self) -> &Basis {
        &self.basis
    }

    /// Original admitted profile declaration.
    #[must_use]
    pub fn profiles(&self) -> &Profiles {
        &self.profiles
    }

    /// Original contract discriminator.
    #[must_use]
    pub fn contract(&self) -> &Contract {
        &self.contract
    }

    /// Opaque optional extensions retained from the source.
    #[must_use]
    pub fn extensions(&self) -> &[Extension] {
        &self.extensions
    }

    /// Sorted module declarations.
    #[must_use]
    pub fn modules(&self) -> &BTreeMap<ModuleDeclarationKey, Module> {
        &self.modules
    }

    /// Sorted Part records.
    #[must_use]
    pub fn parts(&self) -> &BTreeMap<AddressKey, Part> {
        &self.parts
    }

    /// Sorted Joint records.
    #[must_use]
    pub fn joints(&self) -> &BTreeMap<AddressKey, Joint> {
        &self.joints
    }

    /// Sorted Socket records.
    #[must_use]
    pub fn sockets(&self) -> &BTreeMap<AddressKey, Socket> {
        &self.sockets
    }

    /// Sorted Attachment records.
    #[must_use]
    pub fn attachments(&self) -> &BTreeMap<AddressKey, Attachment> {
        &self.attachments
    }

    /// Sorted Region records.
    #[must_use]
    pub fn regions(&self) -> &BTreeMap<AddressKey, Region> {
        &self.regions
    }

    /// Sorted Capability records.
    #[must_use]
    pub fn capabilities(&self) -> &BTreeMap<AddressKey, Capability> {
        &self.capabilities
    }

    /// Sorted Field records.
    #[must_use]
    pub fn fields(&self) -> &BTreeMap<AddressKey, Field> {
        &self.fields
    }

    /// Sorted Landmark owner/role records.
    #[must_use]
    pub fn landmarks(&self) -> &BTreeMap<OwnerRoleKey, Landmark> {
        &self.landmarks
    }

    /// Sorted Dimension owner/role records.
    #[must_use]
    pub fn dimensions(&self) -> &BTreeMap<OwnerRoleKey, Dimension> {
        &self.dimensions
    }

    /// Sorted Frame owner/role records.
    #[must_use]
    pub fn frames(&self) -> &BTreeMap<OwnerRoleKey, Frame> {
        &self.frames
    }
}

fn insert_address_record<T: Clone>(
    collection: &mut std::collections::BTreeMap<AddressKey, T>,
    address: &crate::body_document::Address,
    record: &T,
    collection_name: &'static str,
) -> Result<(), StructuralGraphIndexError> {
    let key = AddressKey::try_from(address).map_err(|error| {
        StructuralGraphIndexError::InvalidAddress {
            collection: collection_name,
            error,
        }
    })?;
    if collection.insert(key.clone(), record.clone()).is_some() {
        return Err(StructuralGraphIndexError::DuplicateAddress { address: key });
    }
    Ok(())
}

fn insert_owner_role_record<T: Clone>(
    collection: &mut std::collections::BTreeMap<OwnerRoleKey, T>,
    owner: &crate::body_document::Address,
    role: &str,
    record: &T,
    collection_name: &'static str,
) -> Result<(), StructuralGraphIndexError> {
    let key = owner_role_key(owner, role).map_err(|error| {
        StructuralGraphIndexError::InvalidOwnerRole {
            collection: collection_name,
            error,
        }
    })?;
    if collection.insert(key.clone(), record.clone()).is_some() {
        return Err(StructuralGraphIndexError::DuplicateOwnerRole {
            collection: collection_name,
            key,
        });
    }
    Ok(())
}

pub(crate) fn owner_role_key(
    owner: &crate::body_document::Address,
    role: &str,
) -> Result<OwnerRoleKey, OwnerRoleKeyError> {
    OwnerRoleKey::from_wire(owner, role)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::body_document::*;
    use serde_json::Number;

    fn number(value: i64) -> Number {
        Number::from(value)
    }

    fn transform() -> RigidTransform {
        RigidTransform {
            translation: [number(0), number(0), number(0)],
            rotation_xyzw: [number(0), number(0), number(0), number(1)],
        }
    }

    fn address(kind: AddressKind, role: &str) -> Address {
        Address {
            namespace: "main".into(),
            anchors: vec![],
            kind,
            role: role.into(),
        }
    }

    fn part(role: &str) -> Part {
        Part {
            address: address(AddressKind::Part, role),
            containment: Containment::Root { root: true },
            placement: transform(),
        }
    }

    fn document(parts: Vec<Part>, modules: Vec<Module>) -> BodyDocument {
        document_with_frames(parts, modules, vec![])
    }

    fn document_with_frames(
        parts: Vec<Part>,
        modules: Vec<Module>,
        frames: Vec<Frame>,
    ) -> BodyDocument {
        BodyDocument {
            contract: Contract {
                family: BODY_CONTRACT_FAMILY.into(),
                revision: number(1),
            },
            source: Source {
                document: "main".into(),
                namespace: "main".into(),
                dependencies: vec![],
            },
            basis: Basis {
                length_unit: LengthUnit::Metre,
                handedness: Handedness::Right,
                up: Axis::PositiveY,
                forward: Axis::PositiveZ,
            },
            profiles: Profiles {
                semantic_numeric: "ck.numeric-frame.r1".into(),
            },
            body: Body {
                modules,
                parts,
                joints: vec![],
                sockets: vec![],
                attachments: vec![],
                landmarks: vec![],
                dimensions: vec![],
                frames,
                regions: vec![],
                capabilities: vec![],
                fields: vec![],
            },
            extensions: vec![],
        }
    }

    fn module(role: &str) -> Module {
        Module {
            declaration: Declaration {
                document: "module".into(),
                namespace: "module".into(),
                anchors: vec!["outer".into()],
                role: role.into(),
            },
            module: "optional".into(),
            root_role: "root".into(),
            instance_anchor: "instance".into(),
            presence: Presence::Absent,
            optional: true,
            attachment_required: false,
            root: None,
        }
    }

    #[test]
    fn admitted_graph_storage_is_sorted_and_permutation_invariant() {
        let first = StructuralBodyGraph::from_admitted(&document(
            vec![part("zeta"), part("alpha")],
            vec![module("zeta"), module("alpha")],
        ))
        .unwrap();
        let second = StructuralBodyGraph::from_admitted(&document(
            vec![part("alpha"), part("zeta")],
            vec![module("alpha"), module("zeta")],
        ))
        .unwrap();

        assert_eq!(first, second);
        let part_roles: Vec<_> = first.parts().keys().map(|key| key.role()).collect();
        assert_eq!(part_roles, vec!["alpha", "zeta"]);
        let module_roles: Vec<_> = first.modules().keys().map(|key| key.role()).collect();
        assert_eq!(module_roles, vec!["alpha", "zeta"]);
        assert_eq!(first.source().namespace, "main");
    }

    #[test]
    fn graph_index_rejects_duplicate_identity_keys_without_overwriting() {
        let result =
            StructuralBodyGraph::from_admitted(&document(vec![part("root"), part("root")], vec![]));
        assert!(matches!(
            result,
            Err(StructuralGraphIndexError::DuplicateAddress { .. })
        ));
    }

    #[test]
    fn graph_index_rejects_duplicate_module_declarations() {
        let result = StructuralBodyGraph::from_admitted(&document(
            vec![],
            vec![module("same"), module("same")],
        ));
        assert!(matches!(
            result,
            Err(StructuralGraphIndexError::DuplicateModuleDeclaration { .. })
        ));
    }

    #[test]
    fn owner_role_records_are_retained_and_permutation_invariant() {
        let root = part("root");
        let first = StructuralBodyGraph::from_admitted(&document_with_frames(
            vec![root.clone()],
            vec![],
            vec![
                Frame {
                    owner: root.address.clone(),
                    role: "z_frame".into(),
                    transform: transform(),
                },
                Frame {
                    owner: root.address.clone(),
                    role: "a_frame".into(),
                    transform: transform(),
                },
            ],
        ))
        .unwrap();
        let second = StructuralBodyGraph::from_admitted(&document_with_frames(
            vec![root.clone()],
            vec![],
            vec![
                Frame {
                    owner: root.address,
                    role: "a_frame".into(),
                    transform: transform(),
                },
                Frame {
                    owner: address(AddressKind::Part, "root"),
                    role: "z_frame".into(),
                    transform: transform(),
                },
            ],
        ))
        .unwrap();

        assert_eq!(first, second);
        let roles: Vec<_> = first.frames().keys().map(|key| key.role()).collect();
        assert_eq!(roles, vec!["a_frame", "z_frame"]);
        assert_eq!(first.frames().len(), 2);
    }

    #[test]
    fn key_construction_is_checked_and_read_only() {
        let declaration = Declaration {
            document: "module".into(),
            namespace: "module".into(),
            anchors: vec!["outer".into()],
            role: "root".into(),
        };
        let key = ModuleDeclarationKey::from_declaration(&declaration).unwrap();
        assert_eq!(key.document(), "module");
        assert_eq!(key.namespace(), "module");
        assert_eq!(key.anchors(), &["outer".to_owned()]);
        assert_eq!(key.role(), "root");
        assert!(
            ModuleDeclarationKey::from_declaration(&Declaration {
                document: "Bad".into(),
                ..declaration.clone()
            })
            .is_err()
        );

        let owner = address(AddressKind::Part, "root");
        let owner_role = OwnerRoleKey::from_wire(&owner, "frame").unwrap();
        assert_eq!(owner_role.owner().role(), "root");
        assert_eq!(owner_role.role(), "frame");
        assert!(OwnerRoleKey::from_wire(&owner, "Bad").is_err());
        let invalid_owner = Address {
            namespace: "Bad".into(),
            ..owner
        };
        assert!(OwnerRoleKey::from_wire(&invalid_owner, "frame").is_err());
    }

    #[test]
    fn malformed_index_input_is_rejected_instead_of_omitted() {
        let malformed = Part {
            address: Address {
                namespace: "main".into(),
                anchors: vec![],
                kind: AddressKind::Part,
                role: "Bad".into(),
            },
            containment: Containment::Root { root: true },
            placement: transform(),
        };
        let result = StructuralBodyGraph::from_admitted(&document(vec![malformed], vec![]));
        assert!(matches!(
            result,
            Err(StructuralGraphIndexError::InvalidAddress { .. })
        ));
    }

    #[test]
    #[should_panic(expected = "structural validation must precede graph indexing")]
    fn from_validated_fails_loud_on_malformed_index_input() {
        let malformed = Part {
            address: Address {
                namespace: "main".into(),
                anchors: vec![],
                kind: AddressKind::Part,
                role: "Bad".into(),
            },
            containment: Containment::Root { root: true },
            placement: transform(),
        };
        let _ = StructuralBodyGraph::from_validated(&document(vec![malformed], vec![]));
    }
}
