#![doc = "Engine-independent Creature Kernel core shell."]

pub mod body_document;
pub mod body_graph;
pub(crate) mod candidate_source_digest_observation;
pub(crate) mod dependency_content_observation;
pub(crate) mod digest;
pub(crate) mod exact_dyadic;
pub mod frame;
mod frame_preparation;
pub mod numeric;
#[cfg(feature = "provisional-r3-numeric-candidate")]
pub mod numeric_comparison;
#[cfg(not(feature = "provisional-r3-numeric-candidate"))]
pub(crate) mod numeric_comparison;
pub mod provisional_form_preview;
#[cfg(feature = "provisional-r3-numeric-candidate")]
pub mod quaternion_normalization;
#[cfg(not(feature = "provisional-r3-numeric-candidate"))]
pub(crate) mod quaternion_normalization;
pub mod reference_placement;
pub(crate) mod resolver_envelope;
pub(crate) mod restricted_snapshot;
pub(crate) mod restricted_source_set_handoff;
pub(crate) mod restricted_source_set_placement;
pub mod semantic_address;
pub mod source_preparation;
pub(crate) mod source_set_preparation;
pub(crate) mod source_set_provenance_observation;
pub mod structural_validation;

/// Implementation convenience for the provisional CLI/debug adapter.  This
/// is not canonical JSON behavior or a stable public serialization contract.
pub use serde_json as provisional_json;
