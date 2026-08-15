//! Crate-private preparation of a supplied source set.
//!
//! This is a deliberately small projection between single-source preparation
//! and a future resolver.  It prepares the designated root and every supplied
//! dependency independently with [`prepare_single_source`], keys the admitted
//! members by their source `(document, namespace)`, retains exact input bytes,
//! and exposes the declarations each member made.  It does not match a
//! declaration by revision identity, acquire or resolve dependencies, merge
//! namespaces, expand modules, assign content or dependency identities,
//! classify resolver statuses, or finalize a snapshot.  Its locator projection
//! only classifies declaration locators against already admitted member keys.
//!
//! The ordering of each member's dependency array remains preserved in that
//! member's exact raw bytes and retained structural source metadata, but it is
//! not semantic for a successful projection: the member map and projected edge
//! list are order-independent.  Supplied dependency position is retained only
//! in provisional error context when one member fails.  Declared dependency
//! edges are sorted by their existing declaration fields (with the owning
//! member as a deterministic tie-breaker); whether a declaration is missing,
//! optional, cyclic, or otherwise resolvable remains resolver-owned.

#![allow(dead_code)]

use crate::body_document::{Dependency, ResourceProfile};
use crate::source_preparation::{PreparedSingleSource, SourcePreparationError};
use std::borrow::Borrow;
use std::collections::BTreeMap;
use std::fmt;

/// Input to the crate-private source-set preparation projection.
///
/// The byte slices are borrowed rather than copied.  The resulting member
/// records retain those exact slices as raw provenance, so the slices must
/// outlive the returned [`PreparedSourceSet`].
#[derive(Debug)]
pub(crate) struct SourceSetInput<'a> {
    /// Exact bytes for the designated root source.
    pub(crate) root: &'a [u8],
    /// Supplied dependency source bytes, in caller-provided order.
    pub(crate) dependencies: Vec<&'a [u8]>,
    /// Resource profile applied independently to every member.
    pub(crate) resource_profile: ResourceProfile,
}

impl<'a> SourceSetInput<'a> {
    /// Construct source-set input from exact root and dependency byte slices.
    pub(crate) fn new(
        root: &'a [u8],
        dependencies: Vec<&'a [u8]>,
        resource_profile: ResourceProfile,
    ) -> Self {
        Self {
            root,
            dependencies,
            resource_profile,
        }
    }
}

/// Stable source-set member key.
///
/// This key contains only the admitted source document and namespace.  It is
/// an index key for this projection, not a content digest or final dependency
/// identity.
#[derive(Clone, Debug, Eq, Hash, Ord, PartialEq, PartialOrd)]
pub(crate) struct SourceSetMemberKey {
    document: String,
    namespace: String,
}

impl SourceSetMemberKey {
    fn from_prepared(prepared: &PreparedSingleSource) -> Self {
        let source = prepared.graph().source();
        Self {
            document: source.document.clone(),
            namespace: source.namespace.clone(),
        }
    }

    /// Source document identifier.
    #[must_use]
    pub(crate) fn document(&self) -> &str {
        &self.document
    }

    /// Source namespace identifier.
    #[must_use]
    pub(crate) fn namespace(&self) -> &str {
        &self.namespace
    }
}

impl fmt::Display for SourceSetMemberKey {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "({}, {})", self.document, self.namespace)
    }
}

/// Role of one prepared source-set member.
#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd)]
pub(crate) enum SourceSetMemberRole {
    /// The designated source-set root.
    Root,
    /// A supplied dependency source.  The supplied position is not semantic.
    Dependency,
}

/// Provisional location used only to identify a failed member preparation.
#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd)]
pub(crate) enum SourceSetMemberLocation {
    /// The designated root source.
    Root,
    /// A supplied dependency at its caller-provided position.
    SuppliedDependency { position: usize },
}

/// One independently prepared source-set member with exact raw provenance.
#[derive(Debug)]
pub(crate) struct SourceSetMember<'a> {
    key: SourceSetMemberKey,
    role: SourceSetMemberRole,
    raw_source: &'a [u8],
    prepared: PreparedSingleSource,
}

impl<'a> SourceSetMember<'a> {
    /// Source-set index key.
    #[must_use]
    pub(crate) fn key(&self) -> &SourceSetMemberKey {
        &self.key
    }

    /// Root/dependency role.  Dependency input position is intentionally not
    /// part of this semantic role.
    #[must_use]
    pub(crate) const fn role(&self) -> SourceSetMemberRole {
        self.role
    }

    /// Exact bytes supplied for this member.
    #[must_use]
    pub(crate) fn raw_source(&self) -> &'a [u8] {
        self.raw_source
    }

    /// Independently prepared source projection.
    #[must_use]
    pub(crate) fn prepared(&self) -> &PreparedSingleSource {
        &self.prepared
    }
}

/// One retained declaration edge from an owning source member.
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct SourceSetDependencyEdge {
    owner: SourceSetMemberKey,
    dependency: Dependency,
}

impl Eq for SourceSetDependencyEdge {}

impl SourceSetDependencyEdge {
    /// Source member that owns the declaration.
    #[must_use]
    pub(crate) fn owner(&self) -> &SourceSetMemberKey {
        &self.owner
    }

    /// Existing source declaration fields, without matching or resolution.
    #[must_use]
    pub(crate) fn dependency(&self) -> &Dependency {
        &self.dependency
    }
}

impl Ord for SourceSetDependencyEdge {
    fn cmp(&self, other: &Self) -> std::cmp::Ordering {
        self.dependency
            .namespace
            .cmp(&other.dependency.namespace)
            .then_with(|| self.dependency.document.cmp(&other.dependency.document))
            .then_with(|| {
                self.dependency
                    .content_sha256
                    .cmp(&other.dependency.content_sha256)
            })
            .then_with(|| self.owner.cmp(&other.owner))
    }
}

impl PartialOrd for SourceSetDependencyEdge {
    fn partial_cmp(&self, other: &Self) -> Option<std::cmp::Ordering> {
        Some(self.cmp(other))
    }
}

/// Locator-only classification of one retained dependency declaration.
///
/// This classification uses only the declaration's `(document, namespace)`
/// locator and the admitted source-set member key.  It does not inspect or
/// compare `content_sha256`; the complete edge is retained so that later
/// resolver work can perform that separate operation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum SourceSetDependencyLocatorResult {
    /// The declaration's locator names an admitted source-set member.
    SuppliedTarget {
        /// The complete declaration edge, including its opaque revision text.
        edge: SourceSetDependencyEdge,
        /// Key of the admitted member named by the declaration locator.
        target: SourceSetMemberKey,
    },
    /// The declaration's locator does not name an admitted source-set member.
    MissingSuppliedTarget {
        /// The complete declaration edge, including its opaque revision text.
        edge: SourceSetDependencyEdge,
    },
}

impl SourceSetDependencyLocatorResult {
    /// Retained declaration edge, including its exact declared revision text.
    #[must_use]
    pub(crate) fn edge(&self) -> &SourceSetDependencyEdge {
        match self {
            Self::SuppliedTarget { edge, .. } | Self::MissingSuppliedTarget { edge } => edge,
        }
    }

    /// Located member key, when the declaration locator was admitted.
    #[must_use]
    pub(crate) fn target(&self) -> Option<&SourceSetMemberKey> {
        match self {
            Self::SuppliedTarget { target, .. } => Some(target),
            Self::MissingSuppliedTarget { .. } => None,
        }
    }
}

/// Failure while preparing the non-resolving source-set projection.
#[derive(Debug, PartialEq)]
pub(crate) enum SourceSetPreparationError {
    /// One source failed its independent single-source preparation.
    Member {
        /// Root or provisional supplied-dependency position.
        location: SourceSetMemberLocation,
        /// Original typed single-source preparation failure.
        error: SourcePreparationError,
    },
    /// Two admitted members claimed one `(document, namespace)` key.
    DuplicateMemberKey { key: SourceSetMemberKey },
}

impl SourceSetPreparationError {
    /// Failed source location, when preparation failed inside one member.
    #[must_use]
    pub(crate) const fn member_location(&self) -> Option<SourceSetMemberLocation> {
        match self {
            Self::Member { location, .. } => Some(*location),
            Self::DuplicateMemberKey { .. } => None,
        }
    }

    /// Original single-source preparation error, when available.
    #[must_use]
    pub(crate) fn member_error(&self) -> Option<&SourcePreparationError> {
        match self {
            Self::Member { error, .. } => Some(error),
            Self::DuplicateMemberKey { .. } => None,
        }
    }

    /// Duplicated source-set key, when available.
    #[must_use]
    pub(crate) fn duplicate_key(&self) -> Option<&SourceSetMemberKey> {
        match self {
            Self::Member { .. } => None,
            Self::DuplicateMemberKey { key } => Some(key),
        }
    }
}

impl fmt::Display for SourceSetPreparationError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Member { location, error } => {
                write!(formatter, "source-set member {location:?} failed: {error}")
            }
            Self::DuplicateMemberKey { key } => {
                write!(formatter, "duplicate source-set member key {key}")
            }
        }
    }
}

impl std::error::Error for SourceSetPreparationError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::Member { error, .. } => Some(error),
            Self::DuplicateMemberKey { .. } => None,
        }
    }
}

/// Deterministic, source-preserving preparation of supplied source members.
///
/// Members are keyed by admitted `(document, namespace)` and are never merged.
/// Dependency declarations are retained as a separately sorted edge list; the
/// locator projection separately classifies whether each edge names an
/// admitted member without interpreting its declared revision.
#[derive(Debug)]
pub(crate) struct PreparedSourceSet<'a> {
    root: SourceSetMemberKey,
    members: BTreeMap<SourceSetMemberKey, SourceSetMember<'a>>,
    dependency_edges: Vec<SourceSetDependencyEdge>,
}

impl<'a> PreparedSourceSet<'a> {
    /// Root member key.
    #[must_use]
    pub(crate) fn root(&self) -> &SourceSetMemberKey {
        &self.root
    }

    /// Deterministically keyed members.
    #[must_use]
    pub(crate) fn members(&self) -> &BTreeMap<SourceSetMemberKey, SourceSetMember<'a>> {
        &self.members
    }

    /// Sorted declared edges, without revision matching or resolution.
    #[must_use]
    pub(crate) fn dependency_edges(&self) -> &[SourceSetDependencyEdge] {
        &self.dependency_edges
    }

    /// Classify every retained declaration by its supplied-member locator.
    ///
    /// Results have exactly the same order and cardinality as
    /// [`Self::dependency_edges`].  This is deliberately only a locator
    /// projection: it does not verify the retained `content_sha256`, acquire
    /// source bytes, or claim dependency resolution.
    #[must_use]
    pub(crate) fn dependency_locator_projection(&self) -> Vec<SourceSetDependencyLocatorResult> {
        self.dependency_edges
            .iter()
            .cloned()
            .map(|edge| {
                let target = SourceSetMemberKey {
                    document: edge.dependency.document.clone(),
                    namespace: edge.dependency.namespace.clone(),
                };
                if self.members.contains_key(&target) {
                    SourceSetDependencyLocatorResult::SuppliedTarget { edge, target }
                } else {
                    SourceSetDependencyLocatorResult::MissingSuppliedTarget { edge }
                }
            })
            .collect()
    }
}

/// Prepare the designated root and supplied dependency bytes independently.
///
/// Every failure returns before exposing a partial set.  The root is prepared
/// first, followed by dependencies in supplied order; that order appears only
/// in [`SourceSetMemberLocation`] for a member-level failure and never in a
/// successful member or edge projection.
pub(crate) fn prepare_source_set<'a, I>(
    input: I,
) -> Result<PreparedSourceSet<'a>, SourceSetPreparationError>
where
    I: Borrow<SourceSetInput<'a>>,
{
    let input = input.borrow();
    let mut members = BTreeMap::new();

    let root_prepared = prepare_member(
        input.root,
        input.resource_profile,
        SourceSetMemberLocation::Root,
    )?;
    let root_key = SourceSetMemberKey::from_prepared(&root_prepared);
    insert_member(
        &mut members,
        root_key.clone(),
        SourceSetMember {
            key: root_key.clone(),
            role: SourceSetMemberRole::Root,
            raw_source: input.root,
            prepared: root_prepared,
        },
    )?;

    for (position, raw_source) in input.dependencies.iter().enumerate() {
        let prepared = prepare_member(
            raw_source,
            input.resource_profile,
            SourceSetMemberLocation::SuppliedDependency { position },
        )?;
        let key = SourceSetMemberKey::from_prepared(&prepared);
        insert_member(
            &mut members,
            key.clone(),
            SourceSetMember {
                key,
                role: SourceSetMemberRole::Dependency,
                raw_source,
                prepared,
            },
        )?;
    }

    let mut dependency_edges = members
        .values()
        .flat_map(|member| {
            member
                .prepared
                .graph()
                .source()
                .dependencies
                .iter()
                .cloned()
                .map(|dependency| SourceSetDependencyEdge {
                    owner: member.key.clone(),
                    dependency,
                })
        })
        .collect::<Vec<_>>();
    dependency_edges.sort();

    Ok(PreparedSourceSet {
        root: root_key,
        members,
        dependency_edges,
    })
}

fn prepare_member(
    raw_source: &[u8],
    resource_profile: ResourceProfile,
    location: SourceSetMemberLocation,
) -> Result<PreparedSingleSource, SourceSetPreparationError> {
    crate::source_preparation::prepare_single_source(raw_source, resource_profile)
        .map_err(|error| SourceSetPreparationError::Member { location, error })
}

fn insert_member<'a>(
    members: &mut BTreeMap<SourceSetMemberKey, SourceSetMember<'a>>,
    key: SourceSetMemberKey,
    member: SourceSetMember<'a>,
) -> Result<(), SourceSetPreparationError> {
    if members.contains_key(&key) {
        return Err(SourceSetPreparationError::DuplicateMemberKey { key });
    }
    members.insert(key, member);
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::body_document::ResourceProfile;

    fn source(document: &str, namespace: &str) -> Vec<u8> {
        let mut value: serde_json::Value = serde_json::from_slice(include_bytes!(
            "../../../examples/body-documents/stylized-digitigrade-biped.json"
        ))
        .expect("example source is valid JSON");
        value["source"]["document"] = serde_json::Value::String(document.to_owned());
        value["source"]["namespace"] = serde_json::Value::String(namespace.to_owned());
        rewrite_namespaces(&mut value["body"], namespace);
        value["source"]["dependencies"] = serde_json::Value::Array(Vec::new());
        serde_json::to_vec(&value).expect("source serializes")
    }

    fn rewrite_namespaces(value: &mut serde_json::Value, namespace: &str) {
        match value {
            serde_json::Value::Object(object) => {
                if object.contains_key("namespace") {
                    object.insert(
                        "namespace".to_owned(),
                        serde_json::Value::String(namespace.to_owned()),
                    );
                }
                for child in object.values_mut() {
                    rewrite_namespaces(child, namespace);
                }
            }
            serde_json::Value::Array(array) => {
                for child in array {
                    rewrite_namespaces(child, namespace);
                }
            }
            _ => {}
        }
    }

    fn with_dependencies(source: &[u8], dependencies: serde_json::Value) -> Vec<u8> {
        let mut value: serde_json::Value = serde_json::from_slice(source).unwrap();
        value["source"]["dependencies"] = dependencies;
        serde_json::to_vec(&value).unwrap()
    }

    fn declaration(document: &str, namespace: &str, marker: char) -> serde_json::Value {
        serde_json::json!({
            "document": document,
            "namespace": namespace,
            "content_sha256": format!("sha256:{}", marker.to_string().repeat(64)),
        })
    }

    fn input<'a>(root: &'a [u8], dependencies: Vec<&'a [u8]>) -> SourceSetInput<'a> {
        SourceSetInput::new(root, dependencies, ResourceProfile::ORDINARY)
    }

    fn semantic_maps_equal(left: &PreparedSingleSource, right: &PreparedSingleSource) -> bool {
        left.basis() == right.basis()
            && left.parts() == right.parts()
            && left.joints() == right.joints()
            && left.sockets() == right.sockets()
            && left.attachments() == right.attachments()
            && left.landmarks() == right.landmarks()
            && left.dimensions() == right.dimensions()
            && left.frames() == right.frames()
    }

    #[test]
    fn valid_members_are_sorted_and_root_is_distinguished() {
        let root = source("root_doc", "root_ns");
        let dependency_b = source("dep_b", "dep_b_ns");
        let dependency_a = source("dep_a", "dep_a_ns");
        let prepared =
            prepare_source_set(input(&root, vec![&dependency_b, &dependency_a])).unwrap();

        let keys: Vec<_> = prepared.members().keys().collect();
        assert_eq!(
            keys.iter()
                .map(|key| (key.document(), key.namespace()))
                .collect::<Vec<_>>(),
            vec![
                ("dep_a", "dep_a_ns"),
                ("dep_b", "dep_b_ns"),
                ("root_doc", "root_ns"),
            ]
        );
        assert_eq!(prepared.root().document(), "root_doc");
        assert_eq!(prepared.root().namespace(), "root_ns");
        assert_eq!(
            prepared
                .members()
                .values()
                .filter(|member| member.role() == SourceSetMemberRole::Root)
                .count(),
            1
        );
        assert!(
            prepared
                .members()
                .values()
                .filter(|member| member.role() == SourceSetMemberRole::Dependency)
                .all(|member| member.key() != prepared.root())
        );
    }

    #[test]
    fn dependency_input_order_does_not_change_successful_projection() {
        let root = source("root_doc", "root_ns");
        let dependency_a = source("dep_a", "dep_a_ns");
        let dependency_b = source("dep_b", "dep_b_ns");
        let first = prepare_source_set(input(&root, vec![&dependency_a, &dependency_b])).unwrap();
        let second = prepare_source_set(input(&root, vec![&dependency_b, &dependency_a])).unwrap();

        assert_eq!(first.root(), second.root());
        assert_eq!(
            first.members().keys().collect::<Vec<_>>(),
            second.members().keys().collect::<Vec<_>>()
        );
        for (key, member) in first.members() {
            let other = second.members().get(key).unwrap();
            assert_eq!(member.role(), other.role());
            assert_eq!(member.raw_source(), other.raw_source());
            assert!(semantic_maps_equal(member.prepared(), other.prepared()));
        }
        assert_eq!(first.dependency_edges(), second.dependency_edges());
    }

    #[test]
    fn duplicate_document_namespace_is_a_typed_key_error() {
        let root = source("same_doc", "same_ns");
        let duplicate = source("same_doc", "same_ns");
        let error = prepare_source_set(input(&root, vec![&duplicate])).unwrap_err();
        assert_eq!(
            error
                .duplicate_key()
                .map(|key| (key.document(), key.namespace())),
            Some(("same_doc", "same_ns"))
        );
        assert!(matches!(
            error,
            SourceSetPreparationError::DuplicateMemberKey { .. }
        ));
    }

    #[test]
    fn raw_bytes_are_retained_while_alternate_formatting_prepares_identically() {
        let compact = source("root_doc", "root_ns");
        let mut value: serde_json::Value = serde_json::from_slice(&compact).unwrap();
        value["source"]["document"] = serde_json::Value::String("formatted_doc".to_owned());
        let formatted = serde_json::to_vec_pretty(&value).unwrap();
        assert_ne!(compact, formatted);
        let prepared = prepare_source_set(input(&compact, vec![&formatted])).unwrap();

        let root_member = prepared
            .members()
            .get(&SourceSetMemberKey {
                document: "root_doc".to_owned(),
                namespace: "root_ns".to_owned(),
            })
            .unwrap();
        assert_eq!(root_member.raw_source(), compact.as_slice());
        let dependency_member = prepared
            .members()
            .values()
            .find(|member| member.role() == SourceSetMemberRole::Dependency)
            .unwrap();
        assert_eq!(dependency_member.raw_source(), formatted.as_slice());
        assert!(semantic_maps_equal(
            root_member.prepared(),
            dependency_member.prepared()
        ));
    }

    #[test]
    fn declarations_are_sorted_and_unmatched_declarations_do_not_fail() {
        let root_without_declarations = source("root_doc", "root_ns");
        let declarations = serde_json::json!([
            declaration("dep_z", "z_ns", 'f'),
            declaration("dep_a", "a_ns", 'a'),
        ]);
        let root = with_dependencies(&root_without_declarations, declarations);
        let prepared = prepare_source_set(input(&root, Vec::new())).unwrap();

        assert_eq!(prepared.members().len(), 1);
        assert_eq!(prepared.dependency_edges().len(), 2);
        let declarations: Vec<_> = prepared
            .dependency_edges()
            .iter()
            .map(|edge| {
                (
                    edge.dependency().namespace.as_str(),
                    edge.dependency().document.as_str(),
                )
            })
            .collect();
        assert_eq!(declarations, vec![("a_ns", "dep_a"), ("z_ns", "dep_z")]);
    }

    #[test]
    fn root_and_supplied_dependency_declarations_locate_supplied_targets() {
        let root = with_dependencies(
            &source("root_doc", "root_ns"),
            serde_json::json!([declaration("dep_doc", "dep_ns", 'a')]),
        );
        let dependency = with_dependencies(
            &source("dep_doc", "dep_ns"),
            serde_json::json!([declaration("leaf_doc", "leaf_ns", 'b')]),
        );
        let leaf = source("leaf_doc", "leaf_ns");
        let prepared = prepare_source_set(input(&root, vec![&dependency, &leaf])).unwrap();

        let projection = prepared.dependency_locator_projection();
        assert_eq!(projection.len(), 2);
        assert!(projection.iter().all(|result| matches!(
            result,
            SourceSetDependencyLocatorResult::SuppliedTarget { .. }
        )));
        assert_eq!(
            projection
                .iter()
                .map(|result| (
                    result.edge().owner().document(),
                    result.target().unwrap().document(),
                ))
                .collect::<Vec<_>>(),
            vec![("root_doc", "dep_doc"), ("dep_doc", "leaf_doc")]
        );
    }

    #[test]
    fn missing_locator_is_classified_without_error_or_panic() {
        let root = with_dependencies(
            &source("root_doc", "root_ns"),
            serde_json::json!([declaration("missing_doc", "missing_ns", 'a')]),
        );
        let prepared = prepare_source_set(input(&root, Vec::new())).unwrap();

        let projection = prepared.dependency_locator_projection();
        assert_eq!(projection.len(), 1);
        assert!(matches!(
            &projection[0],
            SourceSetDependencyLocatorResult::MissingSuppliedTarget { .. }
        ));
        assert_eq!(projection[0].target(), None);
        assert_eq!(
            projection[0].edge().dependency(),
            &Dependency {
                document: "missing_doc".to_owned(),
                namespace: "missing_ns".to_owned(),
                content_sha256: format!("sha256:{}", "a".repeat(64)),
            }
        );
    }

    #[test]
    fn reversed_supplied_member_order_keeps_locator_results_identical() {
        let root = with_dependencies(
            &source("root_doc", "root_ns"),
            serde_json::json!([declaration("dep_doc", "dep_ns", 'a')]),
        );
        let dependency = with_dependencies(
            &source("dep_doc", "dep_ns"),
            serde_json::json!([declaration("leaf_doc", "leaf_ns", 'b')]),
        );
        let leaf = source("leaf_doc", "leaf_ns");
        let first = prepare_source_set(input(&root, vec![&dependency, &leaf])).unwrap();
        let second = prepare_source_set(input(&root, vec![&leaf, &dependency])).unwrap();

        assert_eq!(
            first.dependency_locator_projection(),
            second.dependency_locator_projection()
        );
    }

    #[test]
    fn declared_revision_text_is_retained_but_has_no_locator_effect() {
        let root_a = with_dependencies(
            &source("root_doc", "root_ns"),
            serde_json::json!([declaration("dep_doc", "dep_ns", 'a')]),
        );
        let root_b = with_dependencies(
            &source("root_doc", "root_ns"),
            serde_json::json!([declaration("dep_doc", "dep_ns", 'b')]),
        );
        let dependency = source("dep_doc", "dep_ns");
        let first = prepare_source_set(input(&root_a, vec![&dependency])).unwrap();
        let second = prepare_source_set(input(&root_b, vec![&dependency])).unwrap();
        let first_projection = first.dependency_locator_projection();
        let second_projection = second.dependency_locator_projection();

        assert_eq!(first_projection[0].target(), second_projection[0].target());
        assert_eq!(
            first_projection[0].edge().dependency().document,
            second_projection[0].edge().dependency().document
        );
        assert_ne!(
            first_projection[0].edge().dependency().content_sha256,
            second_projection[0].edge().dependency().content_sha256
        );
        assert!(matches!(
            &first_projection[0],
            SourceSetDependencyLocatorResult::SuppliedTarget { .. }
        ));
        assert!(matches!(
            &second_projection[0],
            SourceSetDependencyLocatorResult::SuppliedTarget { .. }
        ));
    }

    #[test]
    fn every_declared_edge_is_classified_once() {
        let root = with_dependencies(
            &source("root_doc", "root_ns"),
            serde_json::json!([
                declaration("dep_doc", "dep_ns", 'a'),
                declaration("other_doc", "other_ns", 'b')
            ]),
        );
        let dependency = source("dep_doc", "dep_ns");
        let prepared = prepare_source_set(input(&root, vec![&dependency])).unwrap();
        let projection = prepared.dependency_locator_projection();

        assert_eq!(projection.len(), prepared.dependency_edges().len());
        assert_eq!(
            projection
                .iter()
                .map(SourceSetDependencyLocatorResult::edge)
                .collect::<Vec<_>>(),
            prepared.dependency_edges().iter().collect::<Vec<_>>()
        );
    }

    #[test]
    fn extra_undeclared_supplied_member_creates_no_locator_result() {
        let root = source("root_doc", "root_ns");
        let extra = source("extra_doc", "extra_ns");
        let prepared = prepare_source_set(input(&root, vec![&extra])).unwrap();

        assert!(prepared.dependency_edges().is_empty());
        assert!(prepared.dependency_locator_projection().is_empty());
    }

    #[test]
    fn declaration_array_order_is_retained_but_edge_projection_is_order_independent() {
        let base = source("root_doc", "root_ns");
        let a = declaration("dep_a", "a_ns", 'a');
        let b = declaration("dep_b", "b_ns", 'b');
        let first = with_dependencies(&base, serde_json::json!([a.clone(), b.clone()]));
        let second = with_dependencies(&base, serde_json::json!([b, a]));
        let first_bytes = first.clone();
        let second_bytes = second.clone();
        let first = prepare_source_set(input(&first_bytes, Vec::new())).unwrap();
        let second = prepare_source_set(input(&second_bytes, Vec::new())).unwrap();

        let first_member = first.members().get(first.root()).unwrap();
        let second_member = second.members().get(second.root()).unwrap();
        assert_eq!(first_member.raw_source(), first_bytes.as_slice());
        assert_eq!(second_member.raw_source(), second_bytes.as_slice());
        assert_eq!(
            first_member
                .prepared()
                .graph()
                .source()
                .dependencies
                .iter()
                .map(|dependency| (dependency.document.as_str(), dependency.namespace.as_str()))
                .collect::<Vec<_>>(),
            vec![("dep_a", "a_ns"), ("dep_b", "b_ns")]
        );
        assert_eq!(
            second_member
                .prepared()
                .graph()
                .source()
                .dependencies
                .iter()
                .map(|dependency| (dependency.document.as_str(), dependency.namespace.as_str()))
                .collect::<Vec<_>>(),
            vec![("dep_b", "b_ns"), ("dep_a", "a_ns")]
        );
        assert_eq!(first.dependency_edges(), second.dependency_edges());
    }

    #[test]
    fn identical_declarations_use_owner_key_tiebreak_independent_of_input_order() {
        let shared = declaration("shared_dep", "shared_ns", 'a');
        let root = with_dependencies(
            &source("root_doc", "root_ns"),
            serde_json::json!([shared.clone()]),
        );
        let owner_a = with_dependencies(
            &source("owner_a", "owner_a_ns"),
            serde_json::json!([shared.clone()]),
        );
        let owner_b = with_dependencies(
            &source("owner_b", "owner_b_ns"),
            serde_json::json!([shared]),
        );

        let first = prepare_source_set(input(&root, vec![&owner_b, &owner_a])).unwrap();
        let second = prepare_source_set(input(&root, vec![&owner_a, &owner_b])).unwrap();
        let owners = |prepared: &PreparedSourceSet<'_>| {
            prepared
                .dependency_edges()
                .iter()
                .map(|edge| {
                    (
                        edge.owner().document().to_owned(),
                        edge.owner().namespace().to_owned(),
                    )
                })
                .collect::<Vec<_>>()
        };

        assert_eq!(owners(&first), owners(&second));
        assert_eq!(
            owners(&first),
            vec![
                ("owner_a".to_owned(), "owner_a_ns".to_owned()),
                ("owner_b".to_owned(), "owner_b_ns".to_owned()),
                ("root_doc".to_owned(), "root_ns".to_owned()),
            ]
        );
        assert!(first.dependency_edges().iter().all(|edge| edge.dependency()
            == &Dependency {
                document: "shared_dep".to_owned(),
                namespace: "shared_ns".to_owned(),
                content_sha256: format!("sha256:{}", "a".repeat(64)),
            }));
    }

    #[test]
    fn each_member_stays_in_its_own_namespace_and_optional_absence_is_local() {
        let mut root_value: serde_json::Value =
            serde_json::from_slice(&source("root_doc", "root_ns")).unwrap();
        root_value["body"]["modules"]
            .as_array_mut()
            .unwrap()
            .push(serde_json::json!({
                "declaration": {"document": "optional", "namespace": "optional_ns", "anchors": [], "role": "optional_root"},
                "module": "optional", "root_role": "root", "instance_anchor": "optional",
                "presence": "absent", "optional": true, "attachment_required": false
            }));
        let root = serde_json::to_vec(&root_value).unwrap();
        let dependency = source("dep_doc", "dep_ns");
        let prepared = prepare_source_set(input(&root, vec![&dependency])).unwrap();

        for member in prepared.members().values() {
            assert!(
                member
                    .prepared()
                    .parts()
                    .keys()
                    .all(|key| key.namespace() == member.key().namespace())
            );
        }
        let root_member = prepared.members().get(prepared.root()).unwrap();
        assert!(
            root_member
                .prepared()
                .graph()
                .modules()
                .values()
                .any(|module| module.presence == crate::body_document::Presence::Absent)
        );
        assert!(
            !root_member
                .prepared()
                .parts()
                .keys()
                .any(|key| key.anchors().iter().any(|anchor| anchor == "optional"))
        );
        assert!(
            !prepared
                .members()
                .keys()
                .any(|key| key.document() == "optional")
        );
    }

    #[test]
    fn malformed_member_reports_position_and_returns_no_partial_set() {
        let root = source("root_doc", "root_ns");
        let malformed = br"{";
        let error = prepare_source_set(input(&root, vec![malformed])).unwrap_err();
        assert_eq!(
            error.member_location(),
            Some(SourceSetMemberLocation::SuppliedDependency { position: 0 })
        );
        assert!(matches!(
            error.member_error(),
            Some(SourcePreparationError::Admission(_))
        ));
    }
}
