#![doc = "Engine-independent Creature Kernel core shell."]

pub mod body_document;
pub mod body_graph;
pub mod semantic_address;
pub mod structural_validation;

/// Implementation convenience for the provisional CLI/debug adapter.  This
/// is not canonical JSON behavior or a stable public serialization contract.
pub use serde_json as provisional_json;
