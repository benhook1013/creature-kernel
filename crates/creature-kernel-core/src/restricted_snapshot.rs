//! Crate-private, deliberately restricted single-source snapshot handoff.
//!
//! This module is the first concrete in-memory handoff built on the existing
//! admission/preparation and exact reference-placement projections.  It owns
//! the supplied bytes, retains the complete prepared source projection, and
//! retains the exact Part/Attachment placement projection.  It is deliberately
//! not the authoritative resolver `resolve` result and does not activate
//! Readiness 3: dependencies are excluded, canonical frame/value semantics are
//! not applied, and no resolver status or diagnostic envelope is produced.
//!
//! The prepared source and its graph remain source-linked authored records.
//! In particular, the unresolved counts below are an explicit boundary view;
//! they do not represent resolved canonical joints, sockets, landmarks,
//! dimensions, or named-frame values.

#![allow(clippy::result_large_err)]
#![allow(dead_code)]

use crate::body_document::ResourceProfile;
use crate::reference_placement::{
    ExactReferencePlacements, ReferencePlacementError, resolve_exact_integer_reference_placements,
};
use crate::source_preparation::{
    PreparedSingleSource, SourcePreparationError, prepare_single_source,
};
use core::fmt;

/// Counts of source-linked records intentionally left outside this restricted
/// placement projection.
///
/// These are counts of authored/prepared records, not counts of resolved
/// canonical frames or values.  Regions, capabilities, fields, and modules
/// are intentionally not copied into this boundary view: they remain
/// available through [`PreparedSingleSource::graph`].
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct UnresolvedPreparedCounts {
    joints: usize,
    sockets: usize,
    landmarks: usize,
    dimensions: usize,
    named_frames: usize,
}

impl UnresolvedPreparedCounts {
    fn from_prepared(prepared: &PreparedSingleSource) -> Self {
        Self {
            joints: prepared.joints().len(),
            sockets: prepared.sockets().len(),
            landmarks: prepared.landmarks().len(),
            dimensions: prepared.dimensions().len(),
            named_frames: prepared.frames().len(),
        }
    }

    /// Number of authored/prepared Joint records not resolved here.
    #[must_use]
    pub(crate) const fn joints(self) -> usize {
        self.joints
    }

    /// Number of authored/prepared Socket records not resolved here.
    #[must_use]
    pub(crate) const fn sockets(self) -> usize {
        self.sockets
    }

    /// Number of authored/prepared Landmark records not resolved here.
    #[must_use]
    pub(crate) const fn landmarks(self) -> usize {
        self.landmarks
    }

    /// Number of authored/prepared Dimension records not resolved here.
    #[must_use]
    pub(crate) const fn dimensions(self) -> usize {
        self.dimensions
    }

    /// Number of authored/prepared named Frame records not resolved here.
    #[must_use]
    pub(crate) const fn named_frames(self) -> usize {
        self.named_frames
    }
}

/// Failure while constructing the restricted single-source handoff.
///
/// The three failure classes are retained distinctly.  This operation does
/// not map any of them to resolver status or diagnostic codes.
#[derive(Clone, Debug, PartialEq)]
pub(crate) enum RestrictedSingleSourceSnapshotError {
    /// Admission, structural, basis, or numeric source preparation failed.
    SourcePreparation(SourcePreparationError),
    /// The admitted source declared dependencies, which this operation never
    /// acquires, classifies, or verifies.
    DeclaredDependenciesUnsupported { count: usize },
    /// Exact restricted Part/Attachment placement failed.
    ReferencePlacement(ReferencePlacementError),
}

impl fmt::Display for RestrictedSingleSourceSnapshotError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::SourcePreparation(error) => {
                write!(formatter, "source preparation failed: {error}")
            }
            Self::DeclaredDependenciesUnsupported { count } => write!(
                formatter,
                "restricted single-source handoff does not support {count} declared dependencies"
            ),
            Self::ReferencePlacement(error) => {
                write!(formatter, "exact reference placement failed: {error}")
            }
        }
    }
}

impl std::error::Error for RestrictedSingleSourceSnapshotError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::SourcePreparation(error) => Some(error),
            Self::DeclaredDependenciesUnsupported { .. } => None,
            Self::ReferencePlacement(error) => Some(error),
        }
    }
}

/// In-memory preparatory handoff for one admitted, dependency-free source.
///
/// This owns exact source bytes and two source-linked projections.  It is not
/// a resolved graph or an authoritative successful `resolve` snapshot.  The
/// prepared graph remains authored intent/provenance, and only the restricted
/// integer Part/Attachment placement operation contributes derived reference
/// translations.
#[derive(Clone, Debug)]
pub(crate) struct RestrictedSingleSourceSnapshot {
    raw_source: Vec<u8>,
    prepared_source: PreparedSingleSource,
    exact_reference_placements: ExactReferencePlacements,
}

impl RestrictedSingleSourceSnapshot {
    /// Exact bytes supplied to [`build_restricted_single_source_snapshot`].
    #[must_use]
    pub(crate) fn raw_source(&self) -> &[u8] {
        &self.raw_source
    }

    /// Complete source-linked prepared projection, not a resolved graph.
    #[must_use]
    pub(crate) fn prepared_source(&self) -> &PreparedSingleSource {
        &self.prepared_source
    }

    /// Exact integer Part placements and Attachment equation results.
    #[must_use]
    pub(crate) fn exact_reference_placements(&self) -> &ExactReferencePlacements {
        &self.exact_reference_placements
    }

    /// Explicit counts for authored/prepared records left unresolved here.
    #[must_use]
    pub(crate) fn unresolved_prepared_counts(&self) -> UnresolvedPreparedCounts {
        UnresolvedPreparedCounts::from_prepared(&self.prepared_source)
    }
}

/// Build the restricted single-source handoff.
///
/// Preparation runs first, including normal structural validation of
/// declaration syntax.  An admitted dependency declaration then fails before
/// exact placement; this operation neither hashes nor verifies dependency
/// content.  Only after this no-dependency check does the operation run the
/// deliberately narrow exact integer reference-placement projection.  The
/// supplied source bytes are copied into the successful handoff and are never
/// used as an equality or canonical-serialization promise.
pub(crate) fn build_restricted_single_source_snapshot(
    source: &[u8],
    resource_profile: ResourceProfile,
) -> Result<RestrictedSingleSourceSnapshot, RestrictedSingleSourceSnapshotError> {
    let prepared_source = prepare_single_source(source, resource_profile)
        .map_err(RestrictedSingleSourceSnapshotError::SourcePreparation)?;
    let dependency_count = prepared_source.graph().source().dependencies.len();
    if dependency_count != 0 {
        return Err(
            RestrictedSingleSourceSnapshotError::DeclaredDependenciesUnsupported {
                count: dependency_count,
            },
        );
    }
    let exact_reference_placements =
        resolve_exact_integer_reference_placements(&prepared_source)
            .map_err(RestrictedSingleSourceSnapshotError::ReferencePlacement)?;
    Ok(RestrictedSingleSourceSnapshot {
        raw_source: source.to_vec(),
        prepared_source,
        exact_reference_placements,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::reference_placement::{PlacementSource, ReferencePlacementError};
    use serde_json::{Value, json};

    fn example() -> Vec<u8> {
        include_bytes!("../../../examples/body-documents/stylized-digitigrade-biped.json").to_vec()
    }

    fn value() -> Value {
        serde_json::from_slice(&example()).expect("checked-in example is valid JSON")
    }

    fn bytes(value: Value) -> Vec<u8> {
        serde_json::to_vec(&value).expect("fixture mutation is serializable")
    }

    fn part<'a>(
        placements: &'a ExactReferencePlacements,
        role: &str,
        anchors: &[&str],
    ) -> &'a crate::reference_placement::ExactPlacedPart {
        placements
            .parts()
            .values()
            .find(|part| {
                part.address().role() == role
                    && part
                        .address()
                        .anchors()
                        .iter()
                        .map(String::as_str)
                        .eq(anchors.iter().copied())
            })
            .expect("fixture part exists")
    }

    #[test]
    fn stylized_biped_is_owned_and_handed_off_with_explicit_boundary_counts() {
        let source = example();
        let snapshot = build_restricted_single_source_snapshot(&source, ResourceProfile::ORDINARY)
            .expect("checked-in biped satisfies the restricted projection");

        assert_eq!(snapshot.raw_source(), source.as_slice());
        let graph = snapshot.prepared_source().graph();
        assert_eq!(graph.contract().family, "creature-kernel.body");
        assert_eq!(graph.contract().revision.to_string(), "1");
        assert_eq!(graph.source().document, "stylized_digitigrade_biped");
        assert_eq!(graph.source().namespace, "main");
        assert!(graph.source().dependencies.is_empty());
        assert_eq!(graph.modules().len(), 1);
        assert_eq!(graph.regions().len(), 4);
        assert_eq!(graph.capabilities().len(), 3);
        assert!(graph.fields().is_empty());

        let placements = snapshot.exact_reference_placements();
        assert_eq!(placements.parts().len(), 18);
        let pelvis = part(placements, "pelvis", &[]);
        assert_eq!(pelvis.reference_translation().components(), [0, 0, 0]);
        assert_eq!(
            part(placements, "head", &[])
                .reference_translation()
                .components(),
            [0, 3, 0]
        );
        assert_eq!(
            part(placements, "foot", &["left"])
                .reference_translation()
                .components(),
            [-1, -3, 1]
        );
        assert_eq!(
            part(placements, "foot", &["right"])
                .reference_translation()
                .components(),
            [1, -3, 1]
        );
        assert_eq!(
            part(placements, "tail_root", &["tail"])
                .reference_translation()
                .components(),
            [0, 0, -1]
        );

        let tail = part(placements, "tail_root", &["tail"]);
        assert_eq!(tail.source(), PlacementSource::AuthoredAttachment);
        let provenance = tail
            .attachment()
            .expect("tail retains Attachment provenance");
        let attachment = placements
            .attachments()
            .values()
            .next()
            .expect("fixture contains one Attachment");
        assert_eq!(provenance.attachment(), attachment.address());
        assert_eq!(provenance.host_socket(), attachment.host_socket());
        assert_eq!(provenance.mating_socket(), attachment.mating_socket());
        assert_eq!(provenance.offset(), attachment.offset());
        assert_eq!(
            attachment.authored_root_local(),
            attachment.derived_root_local()
        );

        let unresolved = snapshot.unresolved_prepared_counts();
        assert_eq!(unresolved.joints(), 17);
        assert_eq!(unresolved.sockets(), 2);
        assert_eq!(unresolved.landmarks(), 0);
        assert_eq!(unresolved.dimensions(), 0);
        assert_eq!(unresolved.named_frames(), 0);
    }

    #[test]
    fn declared_dependency_is_rejected_after_preparation_without_hash_work() {
        let mut document = value();
        document["source"]["dependencies"] = json!([{
            "document": "unavailable",
            "namespace": "dep_ns",
            "content_sha256": "sha256:0000000000000000000000000000000000000000000000000000000000000000"
        }]);
        let error =
            build_restricted_single_source_snapshot(&bytes(document), ResourceProfile::ORDINARY)
                .expect_err("restricted operation excludes all declared dependencies");
        assert!(matches!(
            error,
            RestrictedSingleSourceSnapshotError::DeclaredDependenciesUnsupported { count: 1 }
        ));
    }

    #[test]
    fn preparation_failures_remain_preparation_failures() {
        let malformed = build_restricted_single_source_snapshot(b"{", ResourceProfile::ORDINARY)
            .expect_err("malformed JSON must fail admission");
        assert!(matches!(
            malformed,
            RestrictedSingleSourceSnapshotError::SourcePreparation(
                SourcePreparationError::Admission(_)
            )
        ));

        let mut structurally_invalid = value();
        structurally_invalid["body"]["parts"] = json!([]);
        let structurally_invalid = build_restricted_single_source_snapshot(
            &bytes(structurally_invalid),
            ResourceProfile::ORDINARY,
        )
        .expect_err("source with no Part root must fail structural validation");
        assert!(matches!(
            structurally_invalid,
            RestrictedSingleSourceSnapshotError::SourcePreparation(
                SourcePreparationError::Structural(_)
            )
        ));
    }

    #[test]
    fn restricted_placement_failures_remain_typed() {
        let mut noncanonical_basis = value();
        noncanonical_basis["basis"]["length_unit"] = json!("centimetre");
        let noncanonical_basis = build_restricted_single_source_snapshot(
            &bytes(noncanonical_basis),
            ResourceProfile::ORDINARY,
        )
        .expect_err("noncanonical basis is outside exact placement scope");
        assert!(matches!(
            noncanonical_basis,
            RestrictedSingleSourceSnapshotError::ReferencePlacement(
                ReferencePlacementError::UnsupportedBasis { .. }
            )
        ));

        let mut nonidentity_rotation = value();
        let neck = nonidentity_rotation["body"]["parts"]
            .as_array_mut()
            .expect("parts array")
            .iter_mut()
            .find(|part| part["address"]["role"] == "neck")
            .expect("neck part");
        neck["placement"]["rotation_xyzw"] = json!([0, 0, 1, 0]);
        let nonidentity_rotation = build_restricted_single_source_snapshot(
            &bytes(nonidentity_rotation),
            ResourceProfile::ORDINARY,
        )
        .expect_err("nonidentity rotations are outside exact placement scope");
        assert!(matches!(
            nonidentity_rotation,
            RestrictedSingleSourceSnapshotError::ReferencePlacement(
                ReferencePlacementError::NonIdentityRotation { .. }
            )
        ));

        let mut noninteger_translation = value();
        let neck = noninteger_translation["body"]["parts"]
            .as_array_mut()
            .expect("parts array")
            .iter_mut()
            .find(|part| part["address"]["role"] == "neck")
            .expect("neck part");
        neck["placement"]["translation"][0] = json!(0.5);
        let noninteger_translation = build_restricted_single_source_snapshot(
            &bytes(noninteger_translation),
            ResourceProfile::ORDINARY,
        )
        .expect_err("fractional translations are outside exact placement scope");
        assert!(matches!(
            noninteger_translation,
            RestrictedSingleSourceSnapshotError::ReferencePlacement(
                ReferencePlacementError::NonIntegerTranslation { .. }
            )
        ));
    }

    #[test]
    fn attachment_disagreement_remains_a_reference_placement_failure() {
        let mut document = value();
        let host = document["body"]["sockets"]
            .as_array_mut()
            .expect("sockets array")
            .iter_mut()
            .find(|socket| socket["address"]["anchors"] == json!([]))
            .expect("host socket");
        host["interface_frame"]["translation"] = json!([0, 0, 0]);
        let error =
            build_restricted_single_source_snapshot(&bytes(document), ResourceProfile::ORDINARY)
                .expect_err("inconsistent Attachment equation must fail");
        assert!(matches!(
            error,
            RestrictedSingleSourceSnapshotError::ReferencePlacement(
                ReferencePlacementError::AttachmentDisagreement { .. }
            )
        ));
    }

    #[test]
    fn source_array_permutations_have_keyed_projection_identity_but_distinct_raw_bytes() {
        let source = example();
        let first = build_restricted_single_source_snapshot(&source, ResourceProfile::ORDINARY)
            .expect("original source");
        let mut reordered = value();
        for collection in [
            "modules",
            "parts",
            "joints",
            "sockets",
            "attachments",
            "regions",
            "capabilities",
        ] {
            reordered["body"][collection]
                .as_array_mut()
                .expect("body collection")
                .reverse();
        }
        let reordered_source = bytes(reordered);
        let second =
            build_restricted_single_source_snapshot(&reordered_source, ResourceProfile::ORDINARY)
                .expect("reordered source");

        assert_ne!(first.raw_source(), second.raw_source());
        assert_eq!(
            first.prepared_source().parts(),
            second.prepared_source().parts()
        );
        assert_eq!(
            first.prepared_source().joints(),
            second.prepared_source().joints()
        );
        assert_eq!(
            first.prepared_source().sockets(),
            second.prepared_source().sockets()
        );
        assert_eq!(
            first.prepared_source().attachments(),
            second.prepared_source().attachments()
        );
        assert_eq!(
            first.exact_reference_placements(),
            second.exact_reference_placements()
        );
    }
}
