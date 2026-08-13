//! Deterministic structural validation for an already admitted body document.
//!
//! This module is intentionally a preparatory Readiness 3 slice.  It checks
//! identity, references, containment, and typed relationships, then builds a
//! source-preserving [`StructuralBodyGraph`].  It does not perform parser or
//! schema admission, canonical serialization/digests, dependency acquisition,
//! numeric/frame normalization, transform composition, or runtime/geometry
//! validation.

use crate::body_document::{Address, AddressKind, BodyDocument, Containment, Presence};
use crate::body_graph::{ModuleDeclarationKey, StructuralBodyGraph, owner_role_key};
use crate::semantic_address::{AddressKey, AddressKeyError, is_identifier, kind_name};
use std::collections::{BTreeMap, BTreeSet};
use std::fmt;

/// Machine-readable structural diagnostic category.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub enum StructuralDiagnosticCategory {
    Address,
    Namespace,
    Module,
    Containment,
    Relation,
    Reference,
    Attachment,
    Owner,
}

impl StructuralDiagnosticCategory {
    /// Stable machine-facing category spelling for diagnostics and adapters.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Address => "address",
            Self::Namespace => "namespace",
            Self::Module => "module",
            Self::Containment => "containment",
            Self::Relation => "relation",
            Self::Reference => "reference",
            Self::Attachment => "attachment",
            Self::Owner => "owner",
        }
    }
}

/// One deterministic structural-validation diagnostic.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct StructuralDiagnostic {
    /// Stable category for consumers and tests.
    pub category: StructuralDiagnosticCategory,
    /// Stable machine-readable code within the category.
    pub code: &'static str,
    /// Relevant identity, where one exists.
    pub address: Option<AddressKey>,
    /// Relevant role (owner role, endpoint role, or field role).
    pub role: Option<String>,
    /// Stable detail sufficient to identify the failed relationship.
    pub detail: String,
}

impl StructuralDiagnostic {
    fn sort_key(
        &self,
    ) -> (
        &StructuralDiagnosticCategory,
        &'static str,
        &Option<AddressKey>,
        &Option<String>,
        &str,
    ) {
        (
            &self.category,
            self.code,
            &self.address,
            &self.role,
            &self.detail,
        )
    }
}

/// A source structural failure.  The result retains all deterministic
/// diagnostics rather than exposing a partial graph.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct StructuralValidationError {
    pub diagnostics: Vec<StructuralDiagnostic>,
}

impl fmt::Display for StructuralValidationError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            formatter,
            "{} structural validation error(s)",
            self.diagnostics.len()
        )
    }
}

impl std::error::Error for StructuralValidationError {}

/// Result of the preparatory structural-validation operation.
#[derive(Clone, Debug, PartialEq)]
pub struct StructuralValidationResult {
    /// Present only when all structural checks succeed.
    pub graph: Option<StructuralBodyGraph>,
    /// Deterministically ordered failures; empty on success.
    pub diagnostics: Vec<StructuralDiagnostic>,
}

impl StructuralValidationResult {
    /// Whether the document passed and a provisional index is available.
    #[must_use]
    pub fn is_valid(&self) -> bool {
        self.graph.is_some() && self.diagnostics.is_empty()
    }

    /// Borrow the provisional graph on success.
    #[must_use]
    pub fn as_graph(&self) -> Option<&StructuralBodyGraph> {
        self.graph.as_ref()
    }

    /// Convert a failed result into a typed error.
    pub fn into_result(self) -> Result<StructuralBodyGraph, StructuralValidationError> {
        match self.graph {
            Some(graph) if self.diagnostics.is_empty() => Ok(graph),
            _ => Err(StructuralValidationError {
                diagnostics: self.diagnostics,
            }),
        }
    }
}

/// Validate one already-admitted [`BodyDocument`] and build its provisional
/// deterministic structural index.  Normal callers supply a document that has
/// already passed admission; this boundary nevertheless defensively checks
/// structural key inputs in source and dependency metadata before indexing.
#[must_use]
pub fn validate_structural_body_document(document: &BodyDocument) -> StructuralValidationResult {
    Validator::new(document).run()
}

/// Short descriptive alias for callers of the structural slice.
#[must_use]
pub fn validate_structural(document: &BodyDocument) -> StructuralValidationResult {
    validate_structural_body_document(document)
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
enum Collection {
    Parts,
    Joints,
    Sockets,
    Attachments,
    Regions,
    Capabilities,
    Fields,
}

impl Collection {
    const fn expected_kind(self) -> AddressKind {
        match self {
            Self::Parts => AddressKind::Part,
            Self::Joints => AddressKind::Joint,
            Self::Sockets => AddressKind::Socket,
            Self::Attachments => AddressKind::Attachment,
            Self::Regions => AddressKind::Region,
            Self::Capabilities => AddressKind::Capability,
            Self::Fields => AddressKind::Field,
        }
    }

    const fn name(self) -> &'static str {
        match self {
            Self::Parts => "parts",
            Self::Joints => "joints",
            Self::Sockets => "sockets",
            Self::Attachments => "attachments",
            Self::Regions => "regions",
            Self::Capabilities => "capabilities",
            Self::Fields => "fields",
        }
    }
}

fn is_sha256_reference(value: &str) -> bool {
    let Some(hex) = value.strip_prefix("sha256:") else {
        return false;
    };
    hex.len() == 64
        && hex
            .bytes()
            .all(|byte| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase())
}

struct Validator<'a> {
    document: &'a BodyDocument,
    diagnostics: Vec<StructuralDiagnostic>,
    identities: BTreeMap<AddressKey, Collection>,
    parts: BTreeMap<AddressKey, usize>,
    joints: BTreeMap<AddressKey, usize>,
    sockets: BTreeMap<AddressKey, usize>,
    modules: BTreeMap<ModuleDeclarationKey, usize>,
    frames_seen: BTreeSet<crate::body_graph::OwnerRoleKey>,
    landmark_roles: BTreeSet<crate::body_graph::OwnerRoleKey>,
    dimension_roles: BTreeSet<crate::body_graph::OwnerRoleKey>,
}

impl<'a> Validator<'a> {
    fn new(document: &'a BodyDocument) -> Self {
        Self {
            document,
            diagnostics: Vec::new(),
            identities: BTreeMap::new(),
            parts: BTreeMap::new(),
            joints: BTreeMap::new(),
            sockets: BTreeMap::new(),
            modules: BTreeMap::new(),
            frames_seen: BTreeSet::new(),
            landmark_roles: BTreeSet::new(),
            dimension_roles: BTreeSet::new(),
        }
    }

    fn run(mut self) -> StructuralValidationResult {
        self.check_source_namespace();
        self.collect_modules();
        self.collect_identity_addresses();
        self.collect_owner_records();
        self.check_modules();
        self.check_parts();
        self.check_joints();
        self.check_sockets();
        self.check_attachments();
        self.check_owned_references();
        self.diagnostics
            .sort_by(|left, right| left.sort_key().cmp(&right.sort_key()));
        self.diagnostics.dedup();
        let graph = if self.diagnostics.is_empty() {
            Some(StructuralBodyGraph::from_validated(self.document))
        } else {
            None
        };
        StructuralValidationResult {
            graph,
            diagnostics: self.diagnostics,
        }
    }

    fn push(
        &mut self,
        category: StructuralDiagnosticCategory,
        code: &'static str,
        address: Option<AddressKey>,
        role: Option<&str>,
        detail: impl Into<String>,
    ) {
        self.diagnostics.push(StructuralDiagnostic {
            category,
            code,
            address,
            role: role.map(str::to_owned),
            detail: detail.into(),
        });
    }

    fn check_source_namespace(&mut self) {
        if !is_identifier(&self.document.source.document) {
            self.push(
                StructuralDiagnosticCategory::Namespace,
                "source-document-invalid",
                None,
                None,
                format!(
                    "source document {:?} is not a restricted identifier",
                    self.document.source.document
                ),
            );
        }
        if !is_identifier(&self.document.source.namespace) {
            self.push(
                StructuralDiagnosticCategory::Namespace,
                "source-namespace-invalid",
                None,
                None,
                format!(
                    "source namespace {:?} is not a restricted identifier",
                    self.document.source.namespace
                ),
            );
        }
        let mut dependency_namespaces = BTreeSet::new();
        for dependency in &self.document.source.dependencies {
            if !is_identifier(&dependency.document) {
                self.push(
                    StructuralDiagnosticCategory::Namespace,
                    "dependency-document-invalid",
                    None,
                    None,
                    format!(
                        "dependency document {:?} is not a restricted identifier",
                        dependency.document
                    ),
                );
            }
            if !is_identifier(&dependency.namespace) {
                self.push(
                    StructuralDiagnosticCategory::Namespace,
                    "dependency-namespace-invalid",
                    None,
                    None,
                    format!(
                        "dependency namespace {:?} is not a restricted identifier",
                        dependency.namespace
                    ),
                );
            }
            if !is_sha256_reference(&dependency.content_sha256) {
                self.push(
                    StructuralDiagnosticCategory::Namespace,
                    "dependency-content-sha256-invalid",
                    None,
                    None,
                    format!(
                        "dependency content hash {:?} is not sha256: plus 64 lowercase hex characters",
                        dependency.content_sha256
                    ),
                );
            }
            if dependency.namespace == self.document.source.namespace {
                self.push(
                    StructuralDiagnosticCategory::Namespace,
                    "dependency-namespace-collision",
                    None,
                    None,
                    format!(
                        "dependency namespace {:?} collides with the source namespace",
                        dependency.namespace
                    ),
                );
            }
            if !dependency_namespaces.insert(dependency.namespace.clone()) {
                self.push(
                    StructuralDiagnosticCategory::Namespace,
                    "dependency-namespace-duplicate",
                    None,
                    None,
                    format!(
                        "dependency namespace {:?} is declared more than once",
                        dependency.namespace
                    ),
                );
            }
        }
    }

    fn collect_modules(&mut self) {
        for (index, module) in self.document.body.modules.iter().enumerate() {
            match ModuleDeclarationKey::from_declaration(&module.declaration) {
                Ok(key) => {
                    if self.modules.insert(key.clone(), index).is_some() {
                        self.push(
                            StructuralDiagnosticCategory::Module,
                            "module-declaration-duplicate",
                            None,
                            Some(&module.declaration.role),
                            format!("module declaration {key:?} is duplicated"),
                        );
                    }
                }
                Err(error) => self.push(
                    StructuralDiagnosticCategory::Module,
                    "module-declaration-invalid",
                    None,
                    Some(&module.declaration.role),
                    error.to_string(),
                ),
            }
        }
    }

    fn collect_identity_addresses(&mut self) {
        let collections = [
            (
                Collection::Parts,
                self.document
                    .body
                    .parts
                    .iter()
                    .enumerate()
                    .map(|(index, record)| (index, &record.address))
                    .collect::<Vec<_>>(),
            ),
            (
                Collection::Joints,
                self.document
                    .body
                    .joints
                    .iter()
                    .enumerate()
                    .map(|(index, record)| (index, &record.address))
                    .collect::<Vec<_>>(),
            ),
            (
                Collection::Sockets,
                self.document
                    .body
                    .sockets
                    .iter()
                    .enumerate()
                    .map(|(index, record)| (index, &record.address))
                    .collect::<Vec<_>>(),
            ),
            (
                Collection::Attachments,
                self.document
                    .body
                    .attachments
                    .iter()
                    .enumerate()
                    .map(|(index, record)| (index, &record.address))
                    .collect::<Vec<_>>(),
            ),
            (
                Collection::Regions,
                self.document
                    .body
                    .regions
                    .iter()
                    .enumerate()
                    .map(|(index, record)| (index, &record.address))
                    .collect::<Vec<_>>(),
            ),
            (
                Collection::Capabilities,
                self.document
                    .body
                    .capabilities
                    .iter()
                    .enumerate()
                    .map(|(index, record)| (index, &record.address))
                    .collect::<Vec<_>>(),
            ),
            (
                Collection::Fields,
                self.document
                    .body
                    .fields
                    .iter()
                    .enumerate()
                    .map(|(index, record)| (index, &record.address))
                    .collect::<Vec<_>>(),
            ),
        ];
        for (collection, addresses) in collections {
            for (index, address) in addresses {
                let key = match AddressKey::try_from(address) {
                    Ok(key) => key,
                    Err(error) => {
                        self.address_error(collection, address, error);
                        continue;
                    }
                };
                if address.namespace != self.document.source.namespace {
                    self.push(
                        StructuralDiagnosticCategory::Namespace,
                        "address-namespace-not-owned",
                        Some(key.clone()),
                        None,
                        format!(
                            "address namespace {:?} is not owned by source namespace {:?}",
                            address.namespace, self.document.source.namespace
                        ),
                    );
                }
                if address.kind != collection.expected_kind() {
                    self.push(
                        StructuralDiagnosticCategory::Address,
                        "address-kind-mismatch",
                        Some(key.clone()),
                        None,
                        format!(
                            "{} collection owns kind {}, found {}",
                            collection.name(),
                            kind_name(&collection.expected_kind()),
                            kind_name(&address.kind)
                        ),
                    );
                }
                if let Some(previous) = self.identities.insert(key.clone(), collection) {
                    self.push(
                        StructuralDiagnosticCategory::Address,
                        "address-duplicate",
                        Some(key.clone()),
                        None,
                        format!("address already occurs in {}", previous.name()),
                    );
                }
                match collection {
                    Collection::Parts => {
                        self.parts.insert(key, index);
                    }
                    Collection::Joints => {
                        self.joints.insert(key, index);
                    }
                    Collection::Sockets => {
                        self.sockets.insert(key, index);
                    }
                    _ => {}
                }
            }
        }
    }

    fn address_error(&mut self, collection: Collection, address: &Address, error: AddressKeyError) {
        self.push(
            StructuralDiagnosticCategory::Address,
            "address-invalid",
            None,
            None,
            format!(
                "{} address {:?} is invalid: {error}",
                collection.name(),
                address
            ),
        );
    }

    fn collect_owner_records(&mut self) {
        for frame in &self.document.body.frames {
            match owner_role_key(&frame.owner, &frame.role) {
                Ok(key) => {
                    if !self.frames_seen.insert(key.clone()) {
                        self.push(
                            StructuralDiagnosticCategory::Owner,
                            "frame-duplicate",
                            Some(key.owner().clone()),
                            Some(key.role()),
                            "frame owner/role is duplicated",
                        );
                    }
                }
                Err(detail) => self.push(
                    StructuralDiagnosticCategory::Owner,
                    "frame-owner-invalid",
                    None,
                    Some(&frame.role),
                    detail.to_string(),
                ),
            }
        }
        for (owner, role, code) in self
            .document
            .body
            .landmarks
            .iter()
            .map(|record| {
                (
                    &record.owner,
                    record.role.as_str(),
                    "landmark-owner-invalid",
                )
            })
            .chain(self.document.body.dimensions.iter().map(|record| {
                (
                    &record.owner,
                    record.role.as_str(),
                    "dimension-owner-invalid",
                )
            }))
            .chain(
                self.document
                    .body
                    .fields
                    .iter()
                    .map(|record| (&record.owner, "", "field-owner-invalid")),
            )
        {
            if code == "field-owner-invalid" {
                if let Err(detail) = AddressKey::try_from(owner).map_err(|error| error.to_string())
                {
                    self.push(
                        StructuralDiagnosticCategory::Owner,
                        code,
                        None,
                        None,
                        detail,
                    );
                }
                continue;
            }
            match crate::body_graph::OwnerRoleKey::from_wire(owner, role) {
                Ok(owner_role) => {
                    let inserted = if code == "landmark-owner-invalid" {
                        self.landmark_roles.insert(owner_role.clone())
                    } else {
                        self.dimension_roles.insert(owner_role.clone())
                    };
                    if !inserted {
                        self.push(
                            StructuralDiagnosticCategory::Owner,
                            if code == "landmark-owner-invalid" {
                                "landmark-duplicate"
                            } else {
                                "dimension-duplicate"
                            },
                            Some(owner_role.owner().clone()),
                            Some(role),
                            "owner/role record is duplicated",
                        );
                    }
                }
                Err(detail) => {
                    self.push(
                        StructuralDiagnosticCategory::Owner,
                        code,
                        None,
                        (!role.is_empty()).then_some(role),
                        detail.to_string(),
                    );
                }
            }
        }
    }

    fn check_modules(&mut self) {
        for module in &self.document.body.modules {
            let declaration = &module.declaration;
            // A declaration's document/namespace identifies the declared
            // module source and is not an embodied identity namespace.  The
            // one-document ownership rule applies to identity-bearing body
            // records and references; rejecting a declaration namespace here
            // would make the admitted optional-module fixture impossible to
            // inspect.
            if !is_identifier(&module.module)
                || !is_identifier(&module.root_role)
                || !is_identifier(&module.instance_anchor)
            {
                self.push(
                    StructuralDiagnosticCategory::Module,
                    "module-field-invalid",
                    None,
                    Some(&declaration.role),
                    "module, root_role, and instance_anchor must be restricted identifiers",
                );
            }
            match (&module.presence, module.root.as_ref()) {
                (Presence::Absent, Some(root)) => self.push(
                    StructuralDiagnosticCategory::Module,
                    "absent-module-has-root",
                    AddressKey::try_from(root).ok(),
                    Some(&declaration.role),
                    "absent module must not reserve an embodied root",
                ),
                (Presence::Absent, None) if !module.optional => self.push(
                    StructuralDiagnosticCategory::Module,
                    "absent-module-flags",
                    None,
                    Some(&declaration.role),
                    "absent module must be optional and not attachment-required",
                ),
                (Presence::Absent, None) => {}
                (Presence::Present, None) => self.push(
                    StructuralDiagnosticCategory::Module,
                    "present-module-missing-root",
                    None,
                    Some(&declaration.role),
                    "present module requires a root Part address",
                ),
                (Presence::Present, Some(root)) => {
                    self.require_part(root, "module-root", Some(&declaration.role));
                }
            }
        }
    }

    fn check_parts(&mut self) {
        let roots: Vec<_> = self
            .document
            .body
            .parts
            .iter()
            .filter(|part| matches!(part.containment, Containment::Root { root: true }))
            .collect();
        if roots.len() != 1 {
            self.push(
                StructuralDiagnosticCategory::Containment,
                "part-root-count",
                None,
                None,
                format!("expected exactly one Part root, found {}", roots.len()),
            );
        }
        let mut parent = BTreeMap::new();
        for part in &self.document.body.parts {
            let Some(key) = AddressKey::try_from(&part.address).ok() else {
                continue;
            };
            match &part.containment {
                Containment::Root { root } if !root => self.push(
                    StructuralDiagnosticCategory::Containment,
                    "part-root-false",
                    Some(key),
                    None,
                    "root containment must carry true",
                ),
                Containment::Root { .. } => {}
                Containment::Parent {
                    parent: parent_address,
                } => {
                    let Some(parent_key) = self.require_part(parent_address, "part-parent", None)
                    else {
                        continue;
                    };
                    parent.insert(key, parent_key);
                }
            }
        }
        if roots.len() == 1 {
            let root = AddressKey::try_from(&roots[0].address).ok();
            let part_keys: Vec<_> = self.parts.keys().cloned().collect();
            for key in part_keys {
                let mut current = key.clone();
                let mut seen = BTreeSet::new();
                loop {
                    if !seen.insert(current.clone()) {
                        self.push(
                            StructuralDiagnosticCategory::Containment,
                            "part-containment-cycle",
                            Some(key.clone()),
                            None,
                            "Part containment contains a cycle",
                        );
                        break;
                    }
                    let Some(next) = parent.get(&current) else {
                        if root.as_ref() != Some(&current) {
                            self.push(
                                StructuralDiagnosticCategory::Containment,
                                "part-disconnected",
                                Some(key.clone()),
                                None,
                                "Part does not connect to the sole root",
                            );
                        }
                        break;
                    };
                    current = next.clone();
                }
            }
        }
    }

    fn check_joints(&mut self) {
        for joint in &self.document.body.joints {
            let Some(joint_key) = AddressKey::try_from(&joint.address).ok() else {
                continue;
            };
            let Some(proximal) = self.require_part(&joint.proximal, "joint-proximal", None) else {
                continue;
            };
            let Some(distal) = self.require_part(&joint.distal, "joint-distal", None) else {
                continue;
            };
            if proximal == distal {
                self.push(
                    StructuralDiagnosticCategory::Relation,
                    "joint-self-relation",
                    Some(joint_key.clone()),
                    None,
                    "Joint proximal and distal Parts must differ",
                );
            }
            let distal_record =
                self.document.body.parts.iter().find(|part| {
                    AddressKey::try_from(&part.address).ok().as_ref() == Some(&distal)
                });
            let immediate = distal_record.is_some_and(|part| matches!(&part.containment, Containment::Parent { parent } if AddressKey::try_from(parent).ok().as_ref() == Some(&proximal)));
            if !immediate {
                self.push(
                    StructuralDiagnosticCategory::Relation,
                    "joint-not-immediate-child",
                    Some(joint_key),
                    None,
                    "Joint distal Part is not the immediate containment child of proximal Part",
                );
            }
        }
    }

    fn check_sockets(&mut self) {
        for socket in &self.document.body.sockets {
            let Some(key) = AddressKey::try_from(&socket.address).ok() else {
                continue;
            };
            self.require_part(&socket.owner, "socket-owner", Some("owner"));
            if socket.owner.kind != AddressKind::Part {
                self.push(
                    StructuralDiagnosticCategory::Relation,
                    "socket-owner-kind",
                    Some(key),
                    Some("owner"),
                    "Socket owner must have kind part",
                );
            }
        }
    }

    fn check_attachments(&mut self) {
        let mut endpoint_use: BTreeMap<AddressKey, Vec<(&'static str, AddressKey)>> =
            BTreeMap::new();
        let mut endpoint_pairs: BTreeMap<(AddressKey, AddressKey), BTreeSet<AddressKey>> =
            BTreeMap::new();
        let containment_parent = self
            .document
            .body
            .parts
            .iter()
            .filter_map(|part| {
                let child = AddressKey::try_from(&part.address).ok()?;
                let Containment::Parent { parent } = &part.containment else {
                    return None;
                };
                Some((child, AddressKey::try_from(parent).ok()?))
            })
            .collect::<BTreeMap<_, _>>();
        let socket_owner: BTreeMap<_, _> = self
            .document
            .body
            .sockets
            .iter()
            .filter_map(|socket| {
                Some((
                    AddressKey::try_from(&socket.address).ok()?,
                    AddressKey::try_from(&socket.owner).ok()?,
                ))
            })
            .collect();
        let mut valid_attachments: Vec<(AddressKey, AddressKey, AddressKey)> = Vec::new();
        for attachment in &self.document.body.attachments {
            let Some(key) = AddressKey::try_from(&attachment.address).ok() else {
                continue;
            };
            let Some(host) = self.require_socket(&attachment.host, "host", Some(&key)) else {
                continue;
            };
            let Some(mating) = self.require_socket(&attachment.mating, "mating", Some(&key)) else {
                continue;
            };
            valid_attachments.push((key.clone(), host.clone(), mating.clone()));
            endpoint_pairs
                .entry((host.clone(), mating.clone()))
                .or_default()
                .insert(key.clone());
            endpoint_use
                .entry(host.clone())
                .or_default()
                .push(("host", key.clone()));
            endpoint_use
                .entry(mating.clone())
                .or_default()
                .push(("mating", key.clone()));
            if host == mating {
                self.push(
                    StructuralDiagnosticCategory::Attachment,
                    "attachment-same-endpoint",
                    Some(key.clone()),
                    None,
                    "Attachment host and mating Socket must differ",
                );
            }
        }
        for ((_host, _mating), attachments) in endpoint_pairs {
            if attachments.len() > 1 {
                let key = attachments
                    .iter()
                    .next()
                    .expect("non-empty repeated endpoint pair");
                self.push(
                    StructuralDiagnosticCategory::Attachment,
                    "attachment-endpoint-pair-duplicate",
                    Some(key.clone()),
                    None,
                    format!(
                        "Attachment host/mating endpoint pair is repeated by {} Attachments",
                        attachments.len()
                    ),
                );
            }
        }
        for (socket, uses) in endpoint_use {
            if uses.len() > 1 {
                self.push(
                    StructuralDiagnosticCategory::Attachment,
                    "socket-capacity-exceeded",
                    Some(socket),
                    None,
                    format!("Socket is used by {} Attachment endpoints", uses.len()),
                );
            }
        }
        for module in &self.document.body.modules {
            if module.presence != Presence::Present || !module.attachment_required {
                continue;
            }
            let Some(root) = module
                .root
                .as_ref()
                .and_then(|root| AddressKey::try_from(root).ok())
            else {
                continue;
            };
            // A module's incoming attachment may mate to a Socket owned by
            // its root or by any contained descendant Part, but its host must
            // be owned by the root's containment parent.  The endpoint owner
            // is structural identity only; no transform composition is
            // implied here.  Keep the broad subtree candidates so the simple
            // one-candidate wrong-host case gets its dedicated diagnostic.
            let subtree_candidates: Vec<_> =
                valid_attachments
                    .iter()
                    .filter_map(|(attachment_key, host, mating)| {
                        let owner = socket_owner.get(mating)?;
                        is_part_in_containment_subtree(owner, &root, &containment_parent)
                            .then_some((attachment_key, host, mating, owner.clone()))
                    })
                    .collect();
            let expected_host_owner = containment_parent.get(&root);
            let matching: Vec<_> = subtree_candidates
                .iter()
                .filter(|(_attachment_key, host, _mating, _owner)| {
                    expected_host_owner.is_some() && socket_owner.get(*host) == expected_host_owner
                })
                .collect();
            if matching.len() == 1 {
                continue;
            }
            if subtree_candidates.len() != 1 {
                self.push(
                    StructuralDiagnosticCategory::Attachment,
                    "module-root-incoming-attachment-count",
                    Some(root),
                    Some(&module.declaration.role),
                    format!(
                        "attachment-required module root has {} matching incoming Attachments, expected one",
                        matching.len()
                    ),
                );
                continue;
            }

            let (_attachment_key, host, _mating, _mating_owner) = &subtree_candidates[0];
            let host_owner = socket_owner.get(*host).cloned();
            if expected_host_owner.is_none() || host_owner.as_ref() != expected_host_owner {
                let expected = expected_host_owner
                    .map(|owner| format!("{owner:?}"))
                    .unwrap_or_else(|| "no containment parent".to_owned());
                let actual = host_owner
                    .map(|owner| format!("{owner:?}"))
                    .unwrap_or_else(|| "missing or invalid host Socket owner".to_owned());
                self.push(
                    StructuralDiagnosticCategory::Attachment,
                    "module-root-host-owner-mismatch",
                    Some(root),
                    Some(&module.declaration.role),
                    format!(
                        "sole incoming Attachment host owner {actual} does not match module root containment parent {expected}"
                    ),
                );
            }
        }
        let module_roots: Vec<_> = self
            .document
            .body
            .modules
            .iter()
            .filter_map(|module| {
                if module.presence != Presence::Present || !module.attachment_required {
                    return None;
                }
                Some((
                    AddressKey::try_from(module.root.as_ref()?).ok()?,
                    module.declaration.role.as_str(),
                ))
            })
            .collect();
        for (attachment_key, host, mating) in &valid_attachments {
            let matches = module_roots
                .iter()
                .filter(|(root, _role)| {
                    let Some(expected_host_owner) = containment_parent.get(root) else {
                        return false;
                    };
                    let Some(host_owner) = socket_owner.get(host) else {
                        return false;
                    };
                    let Some(mating_owner) = socket_owner.get(mating) else {
                        return false;
                    };
                    host_owner == expected_host_owner
                        && is_part_in_containment_subtree(mating_owner, root, &containment_parent)
                })
                .count();
            if matches != 1 {
                self.push(
                    StructuralDiagnosticCategory::Attachment,
                    "attachment-module-root-mismatch",
                    Some(attachment_key.clone()),
                    None,
                    format!(
                        "Attachment matches {matches} present attachment-required module roots, expected exactly one"
                    ),
                );
            }
        }
    }

    fn check_owned_references(&mut self) {
        for region in &self.document.body.regions {
            let Some(key) = AddressKey::try_from(&region.address).ok() else {
                continue;
            };
            for part in &region.parts {
                self.require_part(part, "region-part", Some(&key.to_string()));
            }
        }
        for capability in &self.document.body.capabilities {
            let Some(key) = AddressKey::try_from(&capability.address).ok() else {
                continue;
            };
            for subject in &capability.subjects {
                self.require_identity(subject, "capability-subject", Some(&key));
            }
        }
        for landmark in &self.document.body.landmarks {
            let Some(key) = AddressKey::try_from(&landmark.owner).ok() else {
                continue;
            };
            self.require_identity(&landmark.owner, "landmark-owner", Some(&key));
            self.require_frame(&landmark.frame.owner, &landmark.frame.role, Some(&key));
        }
        for dimension in &self.document.body.dimensions {
            let Some(key) = AddressKey::try_from(&dimension.owner).ok() else {
                continue;
            };
            self.require_identity(&dimension.owner, "dimension-owner", Some(&key));
        }
        for frame in &self.document.body.frames {
            let Some(key) = AddressKey::try_from(&frame.owner).ok() else {
                continue;
            };
            self.require_identity(&frame.owner, "frame-owner", Some(&key));
        }
        for field in &self.document.body.fields {
            let Some(key) = AddressKey::try_from(&field.address).ok() else {
                continue;
            };
            self.require_identity(&field.owner, "field-owner", Some(&key));
            self.require_frame(&field.frame.owner, &field.frame.role, Some(&key));
        }
    }

    fn require_part(
        &mut self,
        address: &Address,
        role: &str,
        context: Option<&str>,
    ) -> Option<AddressKey> {
        let key = self.require_identity(address, role, None)?;
        if address.kind != AddressKind::Part {
            self.push(
                StructuralDiagnosticCategory::Reference,
                "reference-kind-mismatch",
                Some(key.clone()),
                context,
                format!(
                    "{role} requires kind part, found {}",
                    kind_name(&address.kind)
                ),
            );
            return None;
        }
        if !self.parts.contains_key(&key) {
            self.push(
                StructuralDiagnosticCategory::Reference,
                "reference-dangling",
                Some(key.clone()),
                context,
                format!("{role} does not resolve to a Part"),
            );
            return None;
        }
        Some(key)
    }

    fn require_socket(
        &mut self,
        address: &Address,
        role: &str,
        attachment: Option<&AddressKey>,
    ) -> Option<AddressKey> {
        let key = self.require_identity(address, role, attachment)?;
        if address.kind != AddressKind::Socket {
            self.push(
                StructuralDiagnosticCategory::Reference,
                "reference-kind-mismatch",
                Some(key.clone()),
                Some(role),
                format!(
                    "{role} requires kind socket, found {}",
                    kind_name(&address.kind)
                ),
            );
            return None;
        }
        if !self.sockets.contains_key(&key) {
            self.push(
                StructuralDiagnosticCategory::Reference,
                "reference-dangling",
                Some(key.clone()),
                Some(role),
                format!("{role} does not resolve to a Socket"),
            );
            return None;
        }
        Some(key)
    }

    fn require_frame(&mut self, owner: &Address, role: &str, context: Option<&AddressKey>) {
        let Some(owner_key) = self.require_identity(owner, "frame-owner", context) else {
            return;
        };
        let frame_key = match crate::body_graph::OwnerRoleKey::from_wire(owner, role) {
            Ok(key) => key,
            Err(error) => {
                self.push(
                    StructuralDiagnosticCategory::Reference,
                    "frame-reference-invalid",
                    Some(owner_key),
                    Some(role),
                    error.to_string(),
                );
                return;
            }
        };
        if !self.frames_seen.contains(&frame_key) {
            self.push(
                StructuralDiagnosticCategory::Reference,
                "frame-reference-dangling",
                Some(frame_key.owner().clone()),
                Some(role),
                "frame reference does not resolve to a Frame record",
            );
        }
    }

    fn require_identity(
        &mut self,
        address: &Address,
        role: &str,
        context: Option<&AddressKey>,
    ) -> Option<AddressKey> {
        let key = match AddressKey::try_from(address) {
            Ok(key) => key,
            Err(error) => {
                self.push(
                    StructuralDiagnosticCategory::Reference,
                    "reference-address-invalid",
                    None,
                    Some(role),
                    error.to_string(),
                );
                return None;
            }
        };
        if address.namespace != self.document.source.namespace {
            self.push(
                StructuralDiagnosticCategory::Namespace,
                "reference-namespace-not-owned",
                Some(key.clone()),
                Some(role),
                format!(
                    "reference namespace {:?} is not source-owned",
                    address.namespace
                ),
            );
        }
        if !self.identities.contains_key(&key) {
            self.push(
                StructuralDiagnosticCategory::Reference,
                "reference-dangling",
                Some(key.clone()),
                context.map(|_| role).or(Some(role)),
                format!("{role} does not resolve to an identity-bearing concept"),
            );
            return None;
        }
        Some(key)
    }
}

fn is_part_in_containment_subtree(
    candidate: &AddressKey,
    root: &AddressKey,
    parent: &BTreeMap<AddressKey, AddressKey>,
) -> bool {
    let mut current = candidate.clone();
    let mut seen = BTreeSet::new();
    loop {
        if &current == root {
            return true;
        }
        if !seen.insert(current.clone()) {
            return false;
        }
        let Some(next) = parent.get(&current) else {
            return false;
        };
        current = next.clone();
    }
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
    fn part(role: &str, containment: Containment) -> Part {
        Part {
            address: address(AddressKind::Part, role),
            containment,
            placement: transform(),
        }
    }
    fn document(
        parts: Vec<Part>,
        joints: Vec<Joint>,
        sockets: Vec<Socket>,
        attachments: Vec<Attachment>,
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
                modules: vec![],
                parts,
                joints,
                sockets,
                attachments,
                landmarks: vec![],
                dimensions: vec![],
                frames: vec![],
                regions: vec![],
                capabilities: vec![],
                fields: vec![],
            },
            extensions: vec![],
        }
    }

    fn dependency(document: &str, namespace: &str, content_sha256: &str) -> Dependency {
        Dependency {
            document: document.into(),
            namespace: namespace.into(),
            content_sha256: content_sha256.into(),
        }
    }

    fn attachment_required_module(root: &Address, role: &str) -> Module {
        Module {
            declaration: Declaration {
                document: "optional".into(),
                namespace: "optional".into(),
                anchors: vec![],
                role: role.into(),
            },
            module: "optional".into(),
            root_role: "root".into(),
            instance_anchor: "optional".into(),
            presence: Presence::Present,
            optional: true,
            attachment_required: true,
            root: Some(root.clone()),
        }
    }

    fn socket(role: &str, owner: &Address) -> Socket {
        Socket {
            address: address(AddressKind::Socket, role),
            owner: owner.clone(),
            interface_frame: transform(),
        }
    }

    fn attachment(role: &str, host: &Address, mating: &Address) -> Attachment {
        Attachment {
            address: address(AddressKind::Attachment, role),
            host: host.clone(),
            mating: mating.clone(),
            offset: transform(),
        }
    }

    #[test]
    fn successful_one_root_graph_and_array_permutation_invariance() {
        let root = part("root", Containment::Root { root: true });
        let child = part(
            "child",
            Containment::Parent {
                parent: root.address.clone(),
            },
        );
        let first = validate_structural(&document(
            vec![root.clone(), child.clone()],
            vec![],
            vec![],
            vec![],
        ));
        let second = validate_structural(&document(vec![child, root], vec![], vec![], vec![]));
        assert!(first.is_valid());
        assert_eq!(first, second);
    }

    #[test]
    fn source_and_dependency_metadata_keys_are_defensively_checked() {
        let root = part("root", Containment::Root { root: true });
        let mut document = document(vec![root], vec![], vec![], vec![]);
        document.source.document = "Bad".into();
        document.source.dependencies = vec![dependency("dep-ok", "dep-ok", "sha256:bad")];
        let result = validate_structural(&document);
        assert!(result.graph.is_none());
        let codes: Vec<_> = result
            .diagnostics
            .iter()
            .map(|diagnostic| diagnostic.code)
            .collect();
        assert!(codes.contains(&"source-document-invalid"));
        assert!(codes.contains(&"dependency-content-sha256-invalid"));
    }

    #[test]
    fn dependency_metadata_diagnostics_are_permutation_invariant() {
        let root = part("root", Containment::Root { root: true });
        let malformed_a = dependency("Bad", "dep_a", "sha256:bad");
        let malformed_b = dependency("dep_b", "Bad", "sha256:ABC");
        let mut first_document = document(vec![root.clone()], vec![], vec![], vec![]);
        first_document.source.dependencies = vec![malformed_a.clone(), malformed_b.clone()];
        let mut second_document = document(vec![root], vec![], vec![], vec![]);
        second_document.source.dependencies = vec![malformed_b, malformed_a];

        let first = validate_structural(&first_document);
        let second = validate_structural(&second_document);
        assert!(first.graph.is_none());
        assert_eq!(first.diagnostics, second.diagnostics);
        let codes: Vec<_> = first
            .diagnostics
            .iter()
            .map(|diagnostic| diagnostic.code)
            .collect();
        assert!(codes.contains(&"dependency-document-invalid"));
        assert!(codes.contains(&"dependency-namespace-invalid"));
        assert!(codes.contains(&"dependency-content-sha256-invalid"));
    }

    #[test]
    fn absent_optional_module_is_valid_when_the_body_has_a_root() {
        let root = part("root", Containment::Root { root: true });
        let module = Module {
            declaration: Declaration {
                document: "optional".into(),
                namespace: "optional".into(),
                anchors: vec![],
                role: "root".into(),
            },
            module: "optional".into(),
            root_role: "root".into(),
            instance_anchor: "optional".into(),
            presence: Presence::Absent,
            optional: true,
            attachment_required: false,
            root: None,
        };
        let mut document = document(vec![root], vec![], vec![], vec![]);
        document.body.modules.push(module);
        assert!(validate_structural(&document).is_valid());
    }

    #[test]
    fn absent_optional_attachment_required_module_is_valid_when_absent() {
        let root = part("root", Containment::Root { root: true });
        let module = Module {
            declaration: Declaration {
                document: "optional".into(),
                namespace: "optional".into(),
                anchors: vec![],
                role: "root".into(),
            },
            module: "optional".into(),
            root_role: "root".into(),
            instance_anchor: "optional".into(),
            presence: Presence::Absent,
            optional: true,
            attachment_required: true,
            root: None,
        };
        let mut document = document(vec![root], vec![], vec![], vec![]);
        document.body.modules.push(module);
        assert!(validate_structural(&document).is_valid());
    }

    #[test]
    fn present_attachment_required_module_must_be_attached() {
        let root = part("root", Containment::Root { root: true });
        let module_root = part(
            "module_root",
            Containment::Parent {
                parent: root.address.clone(),
            },
        );
        let module = Module {
            declaration: Declaration {
                document: "optional".into(),
                namespace: "optional".into(),
                anchors: vec![],
                role: "root".into(),
            },
            module: "optional".into(),
            root_role: "root".into(),
            instance_anchor: "optional".into(),
            presence: Presence::Present,
            optional: true,
            attachment_required: true,
            root: Some(module_root.address.clone()),
        };
        let mut document = document(vec![root, module_root], vec![], vec![], vec![]);
        document.body.modules.push(module);
        let result = validate_structural(&document);
        assert!(result.graph.is_none());
        assert!(
            result
                .diagnostics
                .iter()
                .any(|diagnostic| diagnostic.code == "module-root-incoming-attachment-count")
        );
    }

    #[test]
    fn descendant_owned_mating_socket_is_accepted_for_present_module() {
        let host = part("host", Containment::Root { root: true });
        let module_root = part(
            "module_root",
            Containment::Parent {
                parent: host.address.clone(),
            },
        );
        let descendant = part(
            "descendant",
            Containment::Parent {
                parent: module_root.address.clone(),
            },
        );
        let host_socket = socket("host_socket", &host.address);
        let mating_socket = socket("mating_socket", &descendant.address);
        let mut document = document(
            vec![host, module_root.clone(), descendant],
            vec![],
            vec![host_socket.clone(), mating_socket.clone()],
            vec![attachment(
                "attach",
                &host_socket.address,
                &mating_socket.address,
            )],
        );
        document
            .body
            .modules
            .push(attachment_required_module(&module_root.address, "module"));
        assert!(validate_structural(&document).is_valid());
    }

    #[test]
    fn module_attachment_rejects_wrong_host_owner() {
        let host = part("host", Containment::Root { root: true });
        let module_root = part(
            "module_root",
            Containment::Parent {
                parent: host.address.clone(),
            },
        );
        let wrong_host = part(
            "wrong_host",
            Containment::Parent {
                parent: host.address.clone(),
            },
        );
        let module_socket = socket("module_socket", &module_root.address);
        let host_socket = socket("host_socket", &wrong_host.address);
        let mut document = document(
            vec![host, module_root.clone(), wrong_host],
            vec![],
            vec![host_socket.clone(), module_socket.clone()],
            vec![attachment(
                "attach",
                &host_socket.address,
                &module_socket.address,
            )],
        );
        document
            .body
            .modules
            .push(attachment_required_module(&module_root.address, "module"));
        let result = validate_structural(&document);
        assert!(result.graph.is_none());
        assert!(
            result
                .diagnostics
                .iter()
                .any(|diagnostic| diagnostic.code == "module-root-host-owner-mismatch")
        );
    }

    #[test]
    fn module_attachment_rejects_multiple_incoming_attachments() {
        let host = part("host", Containment::Root { root: true });
        let module_root = part(
            "module_root",
            Containment::Parent {
                parent: host.address.clone(),
            },
        );
        let descendant = part(
            "descendant",
            Containment::Parent {
                parent: module_root.address.clone(),
            },
        );
        let host_socket_a = socket("host_socket_a", &host.address);
        let host_socket_b = socket("host_socket_b", &host.address);
        let mating_socket_a = socket("mating_socket_a", &module_root.address);
        let mating_socket_b = socket("mating_socket_b", &descendant.address);
        let mut document = document(
            vec![host, module_root.clone(), descendant],
            vec![],
            vec![
                host_socket_a.clone(),
                host_socket_b.clone(),
                mating_socket_a.clone(),
                mating_socket_b.clone(),
            ],
            vec![
                attachment("attach_a", &host_socket_a.address, &mating_socket_a.address),
                attachment("attach_b", &host_socket_b.address, &mating_socket_b.address),
            ],
        );
        document
            .body
            .modules
            .push(attachment_required_module(&module_root.address, "module"));
        let result = validate_structural(&document);
        assert!(result.graph.is_none());
        assert!(
            result
                .diagnostics
                .iter()
                .any(|diagnostic| diagnostic.code == "module-root-incoming-attachment-count")
        );
    }

    #[test]
    fn duplicate_missing_parent_multiple_root_cycle_and_relation_violation() {
        let root = part("root", Containment::Root { root: true });
        let duplicate = root.clone();
        assert!(
            validate_structural(&document(
                vec![root.clone(), duplicate],
                vec![],
                vec![],
                vec![]
            ))
            .graph
            .is_none()
        );
        let missing = part(
            "child",
            Containment::Parent {
                parent: address(AddressKind::Part, "missing"),
            },
        );
        assert!(
            validate_structural(&document(
                vec![root.clone(), missing],
                vec![],
                vec![],
                vec![]
            ))
            .graph
            .is_none()
        );
        let second = part("second", Containment::Root { root: true });
        assert!(
            validate_structural(&document(
                vec![root.clone(), second],
                vec![],
                vec![],
                vec![]
            ))
            .graph
            .is_none()
        );
        let cycle_a = part(
            "a",
            Containment::Parent {
                parent: address(AddressKind::Part, "b"),
            },
        );
        let cycle_b = part(
            "b",
            Containment::Parent {
                parent: address(AddressKind::Part, "a"),
            },
        );
        assert!(
            validate_structural(&document(
                vec![root.clone(), cycle_a, cycle_b],
                vec![],
                vec![],
                vec![]
            ))
            .graph
            .is_none()
        );
        let joint = Joint {
            address: address(AddressKind::Joint, "j"),
            proximal: root.address.clone(),
            distal: address(AddressKind::Part, "missing"),
            proximal_frame: transform(),
            distal_frame: transform(),
        };
        assert!(
            validate_structural(&document(vec![root], vec![joint], vec![], vec![]))
                .graph
                .is_none()
        );
    }

    #[test]
    fn dangling_endpoints_and_socket_cross_role_reuse_are_rejected() {
        let root = part("root", Containment::Root { root: true });
        let socket = Socket {
            address: address(AddressKind::Socket, "s"),
            owner: root.address.clone(),
            interface_frame: transform(),
        };
        let missing = address(AddressKind::Socket, "missing");
        let attachment = Attachment {
            address: address(AddressKind::Attachment, "a"),
            host: socket.address.clone(),
            mating: missing,
            offset: transform(),
        };
        assert!(
            validate_structural(&document(
                vec![root.clone()],
                vec![],
                vec![socket.clone()],
                vec![attachment]
            ))
            .graph
            .is_none()
        );
        let socket2 = Socket {
            address: address(AddressKind::Socket, "s2"),
            owner: root.address.clone(),
            interface_frame: transform(),
        };
        let a1 = Attachment {
            address: address(AddressKind::Attachment, "a1"),
            host: socket.address.clone(),
            mating: socket2.address.clone(),
            offset: transform(),
        };
        let a2 = Attachment {
            address: address(AddressKind::Attachment, "a2"),
            host: socket2.address.clone(),
            mating: socket.address.clone(),
            offset: transform(),
        };
        assert!(
            validate_structural(&document(
                vec![root],
                vec![],
                vec![socket, socket2],
                vec![a1, a2]
            ))
            .graph
            .is_none()
        );
    }

    #[test]
    fn standalone_valid_attachment_is_rejected_without_a_present_module_root() {
        let root = part("root", Containment::Root { root: true });
        let host_socket = socket("host", &root.address);
        let mating_socket = socket("mating", &root.address);
        let result = validate_structural(&document(
            vec![root],
            vec![],
            vec![host_socket.clone(), mating_socket.clone()],
            vec![attachment(
                "standalone",
                &host_socket.address,
                &mating_socket.address,
            )],
        ));
        assert!(result.graph.is_none());
        assert!(result.diagnostics.iter().any(|diagnostic| {
            diagnostic.code == "attachment-module-root-mismatch"
                && diagnostic.address.as_ref().map(AddressKey::role) == Some("standalone")
        }));
    }

    #[test]
    fn repeated_endpoint_pair_diagnostic_is_permutation_invariant() {
        let root = part("root", Containment::Root { root: true });
        let host_socket = socket("host", &root.address);
        let mating_socket = socket("mating", &root.address);
        let first_document = document(
            vec![root],
            vec![],
            vec![host_socket.clone(), mating_socket.clone()],
            vec![
                attachment("a1", &host_socket.address, &mating_socket.address),
                attachment("a2", &host_socket.address, &mating_socket.address),
            ],
        );
        let mut second_document = first_document.clone();
        second_document.body.attachments.reverse();
        let first = validate_structural(&first_document);
        let second = validate_structural(&second_document);
        assert_eq!(first.diagnostics, second.diagnostics);
        let duplicate = first
            .diagnostics
            .iter()
            .find(|diagnostic| diagnostic.code == "attachment-endpoint-pair-duplicate")
            .expect("repeated endpoint pair diagnostic");
        assert_eq!(duplicate.address.as_ref().map(AddressKey::role), Some("a1"));
    }

    #[test]
    fn nested_attachment_required_modules_accept_outer_and_inner_attachments_in_any_order() {
        let world = part("world", Containment::Root { root: true });
        let outer_root = part(
            "outer_root",
            Containment::Parent {
                parent: world.address.clone(),
            },
        );
        let inner_root = part(
            "inner_root",
            Containment::Parent {
                parent: outer_root.address.clone(),
            },
        );
        let outer_host = socket("outer_host", &world.address);
        let outer_mating = socket("outer_mating", &outer_root.address);
        let inner_host = socket("inner_host", &outer_root.address);
        let inner_mating = socket("inner_mating", &inner_root.address);
        let mut first_document = document(
            vec![world, outer_root.clone(), inner_root.clone()],
            vec![],
            vec![
                outer_host.clone(),
                outer_mating.clone(),
                inner_host.clone(),
                inner_mating.clone(),
            ],
            vec![
                attachment(
                    "outer_attachment",
                    &outer_host.address,
                    &outer_mating.address,
                ),
                attachment(
                    "inner_attachment",
                    &inner_host.address,
                    &inner_mating.address,
                ),
            ],
        );
        first_document
            .body
            .modules
            .push(attachment_required_module(&outer_root.address, "outer"));
        first_document
            .body
            .modules
            .push(attachment_required_module(&inner_root.address, "inner"));
        let mut second_document = first_document.clone();
        second_document.body.attachments.reverse();
        second_document.body.sockets.reverse();
        second_document.body.modules.reverse();

        let first = validate_structural(&first_document);
        let second = validate_structural(&second_document);
        assert!(first.is_valid());
        assert_eq!(first, second);
    }

    #[test]
    fn diagnostics_are_stably_ordered() {
        let child = part(
            "child",
            Containment::Parent {
                parent: address(AddressKind::Part, "missing"),
            },
        );
        let root = part("root", Containment::Root { root: true });
        let first = validate_structural(&document(
            vec![child.clone(), root.clone()],
            vec![],
            vec![],
            vec![],
        ));
        let second = validate_structural(&document(vec![root, child], vec![], vec![], vec![]));
        assert_eq!(first.diagnostics, second.diagnostics);
        assert!(
            first
                .diagnostics
                .windows(2)
                .all(|pair| pair[0].sort_key() <= pair[1].sort_key())
        );
    }
}
