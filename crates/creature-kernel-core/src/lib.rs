#![doc = "Engine-independent Creature Kernel core shell."]

pub mod body_document;
pub mod body_graph;
pub(crate) mod exact_dyadic;
pub mod frame;
mod frame_preparation;
pub mod numeric;
pub(crate) mod numeric_comparison;
pub(crate) mod quaternion_normalization;
pub mod reference_placement;
pub(crate) mod resolver_envelope;
pub(crate) mod restricted_snapshot;
pub mod semantic_address;
pub mod source_preparation;
pub(crate) mod source_set_preparation;
pub mod structural_validation;

/// Implementation convenience for the provisional CLI/debug adapter.  This
/// is not canonical JSON behavior or a stable public serialization contract.
pub use serde_json as provisional_json;
