//! Provisional engine-neutral runtime-input handoff.
//!
//! This module owns a transport-only in-memory handoff for independently
//! identified avatar instances. Each instance retains only the exact
//! caller-supplied `instance_id` and the existing [`PreparedSingleSource`]
//! boundary. The instance order supplied by the caller is preserved exactly.
//!
//! This is not a runtime package, serializer, adapter, resolver snapshot, or
//! Readiness 3 implementation. It carries no additional metadata and does not
//! prepare source bytes.

use core::fmt;
use creature_kernel_core::source_preparation::PreparedSingleSource;
use std::collections::BTreeSet;

/// Failure while constructing the provisional runtime-input handoff.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum ProvisionalRuntimeInputError {
    /// No avatar instance was supplied.
    EmptyInstances,
    /// An avatar instance had no host-facing identity.
    EmptyInstanceId,
    /// Two ordered instances used the same host-facing identity.
    DuplicateInstanceId { instance_id: String },
}

impl fmt::Display for ProvisionalRuntimeInputError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::EmptyInstances => write!(formatter, "at least one avatar instance is required"),
            Self::EmptyInstanceId => write!(formatter, "instance_id must not be empty"),
            Self::DuplicateInstanceId { instance_id } => {
                write!(
                    formatter,
                    "duplicate runtime-input instance_id {instance_id:?}"
                )
            }
        }
    }
}

impl std::error::Error for ProvisionalRuntimeInputError {}

/// One independently identified avatar's provisional runtime input.
///
/// The prepared source is moved into this owned handoff. It remains the
/// source-linked projection produced by
/// [`creature_kernel_core::source_preparation::prepare_single_source`]; this type does not
/// promote it to a resolved snapshot or package.
#[derive(Clone, Debug)]
pub struct ProvisionalRuntimeAvatarInput {
    instance_id: String,
    prepared_source: PreparedSingleSource,
}

impl ProvisionalRuntimeAvatarInput {
    /// Construct one transport entry from an exact instance identity and an
    /// already prepared source.
    pub fn new(
        instance_id: impl Into<String>,
        prepared_source: PreparedSingleSource,
    ) -> Result<Self, ProvisionalRuntimeInputError> {
        let input = Self {
            instance_id: instance_id.into(),
            prepared_source,
        };
        input.validate()?;
        Ok(input)
    }

    /// Exact caller-supplied runtime instance identity.
    #[must_use]
    pub fn instance_id(&self) -> &str {
        &self.instance_id
    }

    /// Existing source-linked prepared projection for this avatar.
    #[must_use]
    pub fn prepared_source(&self) -> &PreparedSingleSource {
        &self.prepared_source
    }

    fn validate(&self) -> Result<(), ProvisionalRuntimeInputError> {
        if self.instance_id.is_empty() {
            return Err(ProvisionalRuntimeInputError::EmptyInstanceId);
        }
        Ok(())
    }
}

/// Ordered provisional runtime input for one or more independently identified
/// avatars.
///
/// `instances()` is the host handoff order. No sorting is applied. Duplicate
/// `instance_id` values are rejected because they would make a host-side
/// per-avatar lookup ambiguous.
#[derive(Clone, Debug)]
pub struct ProvisionalRuntimeInput {
    instances: Vec<ProvisionalRuntimeAvatarInput>,
}

impl ProvisionalRuntimeInput {
    /// Ordered per-avatar transport entries retained by this handoff.
    #[must_use]
    pub fn instances(&self) -> &[ProvisionalRuntimeAvatarInput] {
        &self.instances
    }
}

/// Build an owned provisional runtime-input handoff from already prepared
/// avatar sources.
///
/// Validation is fail-closed: no handoff is returned for an empty collection,
/// an empty `instance_id`, or a duplicate `instance_id`. The function does not
/// prepare source bytes itself, so callers cannot bypass the existing
/// [`PreparedSingleSource`] boundary through this API.
pub fn handoff_provisional_runtime_input(
    instances: Vec<ProvisionalRuntimeAvatarInput>,
) -> Result<ProvisionalRuntimeInput, ProvisionalRuntimeInputError> {
    if instances.is_empty() {
        return Err(ProvisionalRuntimeInputError::EmptyInstances);
    }

    let mut instance_ids = BTreeSet::new();
    for instance in &instances {
        instance.validate()?;
        if !instance_ids.insert(instance.instance_id.clone()) {
            return Err(ProvisionalRuntimeInputError::DuplicateInstanceId {
                instance_id: instance.instance_id.clone(),
            });
        }
    }

    Ok(ProvisionalRuntimeInput { instances })
}

#[cfg(test)]
mod tests {
    use super::*;
    use creature_kernel_core::body_document::ResourceProfile;
    use creature_kernel_core::source_preparation::prepare_single_source;

    const BASE_SOURCE: &[u8] =
        include_bytes!("../../../examples/body-documents/stylized-digitigrade-biped.json");
    const AUTHORED_SOURCE: &[u8] = include_bytes!(
        "../../../examples/body-documents/stylized-digitigrade-biped-authored-form.json"
    );

    fn prepared(source: &[u8]) -> PreparedSingleSource {
        prepare_single_source(source, ResourceProfile::ORDINARY)
            .expect("checked-in example source prepares")
    }

    fn avatar(instance_id: &str, source: &[u8]) -> ProvisionalRuntimeAvatarInput {
        ProvisionalRuntimeAvatarInput::new(instance_id, prepared(source))
            .expect("test instance identity is valid")
    }

    fn transport_projection(input: &ProvisionalRuntimeInput) -> Vec<(String, String)> {
        input
            .instances()
            .iter()
            .map(|instance| {
                (
                    instance.instance_id().to_owned(),
                    instance.prepared_source().graph().source().document.clone(),
                )
            })
            .collect()
    }

    #[test]
    fn preserves_ordered_instance_ids_and_corresponding_prepared_sources() {
        let handoff = handoff_provisional_runtime_input(vec![
            avatar("avatar-right", AUTHORED_SOURCE),
            avatar("avatar-left", BASE_SOURCE),
        ])
        .expect("ordered runtime input succeeds");

        assert_eq!(
            transport_projection(&handoff),
            vec![
                (
                    "avatar-right".to_owned(),
                    "stylized_digitigrade_biped_authored_form".to_owned(),
                ),
                (
                    "avatar-left".to_owned(),
                    "stylized_digitigrade_biped".to_owned(),
                ),
            ]
        );
    }

    #[test]
    fn repeated_handoff_is_deterministic_without_reordering() {
        let build = || {
            handoff_provisional_runtime_input(vec![
                avatar("zeta-instance", AUTHORED_SOURCE),
                avatar("alpha-instance", BASE_SOURCE),
            ])
            .expect("deterministic runtime input succeeds")
        };

        let first = build();
        let second = build();

        assert_eq!(transport_projection(&first), transport_projection(&second));
        assert_eq!(first.instances()[0].instance_id(), "zeta-instance");
        assert_eq!(first.instances()[1].instance_id(), "alpha-instance");
    }

    #[test]
    fn duplicate_instance_id_rejects_the_whole_handoff() {
        let result = handoff_provisional_runtime_input(vec![
            avatar("first-instance", BASE_SOURCE),
            avatar("same-instance", BASE_SOURCE),
            avatar("same-instance", AUTHORED_SOURCE),
            avatar("later-instance", AUTHORED_SOURCE),
        ]);

        assert_eq!(
            result.unwrap_err(),
            ProvisionalRuntimeInputError::DuplicateInstanceId {
                instance_id: "same-instance".to_owned(),
            }
        );
    }

    #[test]
    fn empty_collection_and_instance_identity_fail_closed() {
        assert_eq!(
            handoff_provisional_runtime_input(Vec::new()).unwrap_err(),
            ProvisionalRuntimeInputError::EmptyInstances
        );
        assert_eq!(
            ProvisionalRuntimeAvatarInput::new("", prepared(BASE_SOURCE)).unwrap_err(),
            ProvisionalRuntimeInputError::EmptyInstanceId
        );
    }

    #[test]
    fn source_preparation_remains_an_explicit_upstream_failure() {
        let source_error = prepare_single_source(br"{", ResourceProfile::ORDINARY).unwrap_err();
        assert!(matches!(
            source_error,
            creature_kernel_core::source_preparation::SourcePreparationError::Admission(_)
        ));
    }
}
