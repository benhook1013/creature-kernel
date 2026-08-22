//! Provisional CLI adapter for the display-only filled-form descriptor slice.
//!
//! This command is intentionally a developer inspection operation.  Its
//! payload contains exact integer source points, source-authored shape
//! dimensions, and fixed profile tuning; it does not publish geometry, mesh,
//! SDF, anatomy, runtime, or Readiness 3 output.

use creature_kernel_core::body_document::{ResourceProfile, Status as AdmissionStatus};
use creature_kernel_core::provisional_form_preview::{
    MAX_PROVISIONAL_PERMILLE, ProvisionalFormPreview, ProvisionalFormPreviewError,
    ProvisionalPlacementFailureKind, ProvisionalShape, ProvisionalSourceFailureKind,
    build_provisional_form_preview,
};
use creature_kernel_core::provisional_json::{Map, Value, json};
use creature_kernel_core::reference_placement::PlacementSource;
use creature_kernel_core::semantic_address::AddressKey;
use creature_kernel_core::source_preparation::{
    PreparedSingleSource, SourcePreparationError, prepare_single_source,
};
use std::collections::{BTreeMap, BTreeSet};
use std::fmt;
use std::path::Path;

const FORMAT: &str = "creature-kernel.provisional-form-preview.v5";
const OPERATION: &str = "inspect-provisional-form";
const AUTHORED_DIMENSION_PROVENANCE: &str = "source-authored";
const SHAPE_BASIS_PROVENANCE: &str = "source-authored-dimensions-plus-fixed-display-factor";
const LIMITATIONS: &str = "Provisional display-only filled-form descriptors from the restricted single-source exact Part placement projection; source-authored dimensions are consumed only through the closed provisional shape-control vocabulary and fixed display profile factors remain applied; no production geometry, mesh, SDF, topology, collision, rig, skin, anatomy, Joint-frame interpretation, landmarks, frames, general units or rotations, dependency resolution, canonical snapshot/serialization, runtime claim, or Readiness activation. Descriptors are not graph Parts.";

struct PreparedAuthoredDimensions {
    inventory: Vec<AuthoredDimension>,
    values: BTreeMap<(AddressKey, String), u32>,
}

struct AuthoredDimension {
    owner: AddressKey,
    role: String,
    value_permille: u32,
    document: String,
    namespace: String,
}

impl AuthoredDimension {
    fn owner(&self) -> &AddressKey {
        &self.owner
    }

    fn role(&self) -> &str {
        &self.role
    }

    const fn value_permille(&self) -> u32 {
        self.value_permille
    }

    fn provenance(&self) -> AuthoredDimensionProvenance<'_> {
        AuthoredDimensionProvenance {
            document: &self.document,
            namespace: &self.namespace,
        }
    }
}

struct AuthoredDimensionProvenance<'a> {
    document: &'a str,
    namespace: &'a str,
}

impl AuthoredDimensionProvenance<'_> {
    const fn source(&self) -> &'static str {
        AUTHORED_DIMENSION_PROVENANCE
    }

    const fn document(&self) -> &str {
        self.document
    }

    const fn namespace(&self) -> &str {
        self.namespace
    }
}

#[derive(Debug)]
enum InspectionError {
    Core(ProvisionalFormPreviewError),
    MissingAuthoredDimension {
        address: AddressKey,
        role: String,
    },
    InvalidAuthoredDimension {
        address: AddressKey,
        role: String,
        value: String,
    },
}

impl fmt::Display for InspectionError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Core(error) => error.fmt(formatter),
            Self::MissingAuthoredDimension { address, role } => write!(
                formatter,
                "required source-authored dimension {role:?} is missing at {address}"
            ),
            Self::InvalidAuthoredDimension {
                address,
                role,
                value,
            } => write!(
                formatter,
                "source-authored dimension {role:?} at {address} has invalid positive permille value {value}"
            ),
        }
    }
}

/// Serialized result and process status for one CLI invocation.
#[derive(Debug, PartialEq)]
pub(crate) struct CliResult {
    pub json: String,
    pub exit_code: i32,
}

/// Run the command-line adapter over process arguments after the executable.
pub(crate) fn run_cli<I, S>(arguments: I) -> CliResult
where
    I: IntoIterator<Item = S>,
    S: Into<String>,
{
    let arguments: Vec<String> = arguments.into_iter().map(Into::into).collect();
    if let Some(help) = help_response(&arguments) {
        return result(help);
    }
    let Some(input) = parse_input_path(&arguments) else {
        return result(usage_error(
            "usage: creature-kernel inspect-provisional-form --input <path> (use '-' for stdin)",
        ));
    };
    let source = match crate::structural_inspection::read_input(input) {
        Ok(source) => source,
        Err(error) => return result(input_error(error.to_string())),
    };
    inspect_source(&source)
}

fn help_response(arguments: &[String]) -> Option<Value> {
    if !matches!(
        arguments,
        [command, flag]
            if command == OPERATION && (flag == "--help" || flag == "-h")
    ) {
        return None;
    }
    let mut output = base_output("help");
    output.insert("status".to_owned(), Value::String("success".to_owned()));
    output.insert("processing_complete".to_owned(), Value::Bool(true));
    output.insert("diagnostics_complete".to_owned(), Value::Bool(true));
    output.insert("diagnostics".to_owned(), Value::Array(Vec::new()));
    output.insert(
        "help".to_owned(),
        json!({
            "usage": "creature-kernel inspect-provisional-form --input <path> (use '-' for stdin)",
            "description": "Inspect the four fixed display-only provisional filled-form variants.",
            "options": [
                {"flag": "--input <path>", "description": "Read a body document from a file (use '-' for stdin)."},
                {"flag": "--help", "description": "Show this structured help response."}
            ]
        }),
    );
    Some(Value::Object(output))
}

fn parse_input_path(arguments: &[String]) -> Option<&Path> {
    if arguments.first().map(String::as_str) != Some(OPERATION) {
        return None;
    }
    let mut input = None;
    let mut index = 1;
    while index < arguments.len() {
        if arguments[index] != "--input" || input.is_some() {
            return None;
        }
        index += 1;
        let value = arguments.get(index)?;
        if value.starts_with('-') && value != "-" {
            return None;
        }
        input = Some(Path::new(value));
        index += 1;
    }
    input
}

/// Inspect already-acquired source bytes.
pub(crate) fn inspect_source(source: &[u8]) -> CliResult {
    match build_provisional_form_preview(source, ResourceProfile::ORDINARY) {
        Ok(preview) => match prepare_single_source(source, ResourceProfile::ORDINARY) {
            Ok(prepared) => match prepare_authored_dimensions(&preview, &prepared) {
                Ok(dimensions) => match success(preview, &dimensions) {
                    Ok(result) => result,
                    Err(error) => failure(error),
                },
                Err(error) => failure(error),
            },
            Err(error) => failure(InspectionError::Core(map_source_preparation_error(error))),
        },
        Err(error) => failure(InspectionError::Core(error)),
    }
}

fn success(
    preview: ProvisionalFormPreview,
    dimensions: &PreparedAuthoredDimensions,
) -> Result<CliResult, InspectionError> {
    let output = json!({
        "format": FORMAT,
        "operation": OPERATION,
        "status": "success",
        "stage": "provisional-form",
        "processing_complete": true,
        "diagnostics_complete": true,
        "diagnostics": [],
        "source": {
            "document": preview.source().document(),
            "namespace": preview.source().namespace(),
            "resource_profile_id": preview.resource_profile_id(),
        },
        "reference_scale": {
            "parent": crate::structural_inspection::address_key_value(preview.reference_scale().parent()),
            "child": crate::structural_inspection::address_key_value(preview.reference_scale().child()),
            "axis_delta": exact_translation_value(preview.reference_scale().axis_delta()),
            "squared_length": preview.reference_scale().squared_length(),
            "source": "exact-containment-edge",
        },
        "authored_dimensions": dimensions.inventory.iter().map(authored_dimension_value).collect::<Vec<_>>(),
        "variants": preview.variants().iter().map(|variant| variant_value(variant, dimensions)).collect::<Result<Vec<_>, _>>()?,
        "limitations": LIMITATIONS,
    });
    Ok(result(output))
}

fn variant_value(
    variant: &creature_kernel_core::provisional_form_preview::ProvisionalFormVariant,
    dimensions: &PreparedAuthoredDimensions,
) -> Result<Value, InspectionError> {
    Ok(json!({
        "id": variant.id(),
        "profile_id": variant.provenance().profile_id(),
        "provenance": {
            "source": variant.provenance().source(),
            "resource_profile_id": variant.provenance().resource_profile_id(),
            "shape_basis": SHAPE_BASIS_PROVENANCE,
        },
        "descriptors": variant.descriptors().iter().map(|descriptor| descriptor_value(descriptor, variant.id(), dimensions)).collect::<Result<Vec<_>, _>>()?,
    }))
}

fn descriptor_value(
    descriptor: &creature_kernel_core::provisional_form_preview::ProvisionalPartDescriptor,
    profile_id: &'static str,
    dimensions: &PreparedAuthoredDimensions,
) -> Result<Value, InspectionError> {
    let dimension_roles = authored_dimension_roles(descriptor.address().role())
        .expect("core preview role is in the closed provisional shape vocabulary");
    Ok(json!({
        "descriptor_kind": "display-only-form-descriptor",
        "address": crate::structural_inspection::address_key_value(descriptor.address()),
        "parent": descriptor.parent().map(crate::structural_inspection::address_key_value).unwrap_or(Value::Null),
        "placement_source": placement_source_name(descriptor.placement_source()),
        "reference_point": exact_translation_value(descriptor.reference_point()),
        "dimension_roles": dimension_roles,
        "profile_id": descriptor.provenance().profile_id(),
        "source": descriptor.provenance().source(),
        "provenance": {
            "source": descriptor.provenance().source(),
            "resource_profile_id": descriptor.provenance().resource_profile_id(),
            "shape_basis": SHAPE_BASIS_PROVENANCE,
        },
        "shape": shape_value(descriptor.shape(), profile_id, descriptor.address(), dimensions)?,
    }))
}

fn authored_dimension_value(dimension: &AuthoredDimension) -> Value {
    json!({
        "owner": crate::structural_inspection::address_key_value(dimension.owner()),
        "role": dimension.role(),
        "value_permille": dimension.value_permille(),
        "provenance": {
            "source": dimension.provenance().source(),
            "document": dimension.provenance().document(),
            "namespace": dimension.provenance().namespace(),
        },
    })
}

fn shape_value(
    shape: &ProvisionalShape,
    profile_id: &'static str,
    address: &AddressKey,
    dimensions: &PreparedAuthoredDimensions,
) -> Result<Value, InspectionError> {
    match shape {
        ProvisionalShape::Ellipsoid { center, .. } => Ok(json!({
            "name": "ellipsoid",
            "center": exact_translation_value(*center),
            "axis_extents_permille": extents(profile_id, address, dimensions)?,
        })),
        ProvisionalShape::Capsule { from, to, .. } => Ok(json!({
            "name": "capsule",
            "from": exact_translation_value(*from),
            "to": exact_translation_value(*to),
            "radius_permille": radius(profile_id, address, dimensions)?,
        })),
        ProvisionalShape::TaperedSegment { from, to, .. } => {
            let (start, end) = taper_radii(profile_id, address, dimensions)?;
            Ok(json!({
            "name": "tapered-segment",
            "from": exact_translation_value(*from),
            "to": exact_translation_value(*to),
            "start_radius_permille": start,
            "end_radius_permille": end,
            }))
        }
    }
}

fn prepare_authored_dimensions(
    preview: &ProvisionalFormPreview,
    prepared: &PreparedSingleSource,
) -> Result<PreparedAuthoredDimensions, InspectionError> {
    let mut required = BTreeSet::new();
    for variant in preview.variants() {
        for descriptor in variant.descriptors() {
            for role in authored_dimension_roles(descriptor.address().role())
                .expect("core preview role is in the closed provisional shape vocabulary")
            {
                required.insert((descriptor.address().clone(), (*role).to_owned()));
            }
        }
    }

    let mut values = BTreeMap::new();
    for (owner_role, value) in prepared.dimensions() {
        let key = (owner_role.owner().clone(), owner_role.role().to_owned());
        if !required.contains(&key) {
            continue;
        }
        let exact = match value.to_exact_i64() {
            Ok(exact) => exact,
            Err(cause) => {
                return Err(InspectionError::InvalidAuthoredDimension {
                    address: key.0,
                    role: key.1,
                    value: format!("bits=0x{:016x} ({cause})", value.to_bits()),
                });
            }
        };
        let value_permille = match u32::try_from(exact) {
            Ok(value_permille) if (1..=i64::from(MAX_PROVISIONAL_PERMILLE)).contains(&exact) => {
                value_permille
            }
            _ => {
                return Err(InspectionError::InvalidAuthoredDimension {
                    address: key.0,
                    role: key.1,
                    value: format!("integer={exact} bits=0x{:016x}", value.to_bits()),
                });
            }
        };
        values.insert(key, value_permille);
    }

    for (address, role) in &required {
        if !values.contains_key(&(address.clone(), role.clone())) {
            return Err(InspectionError::MissingAuthoredDimension {
                address: address.clone(),
                role: role.clone(),
            });
        }
    }

    let source = prepared.graph().source();
    let inventory = values
        .iter()
        .map(|((owner, role), value_permille)| AuthoredDimension {
            owner: owner.clone(),
            role: role.clone(),
            value_permille: *value_permille,
            document: source.document.clone(),
            namespace: source.namespace.clone(),
        })
        .collect();
    Ok(PreparedAuthoredDimensions { inventory, values })
}

fn authored_dimension_roles(role: &str) -> Option<&'static [&'static str]> {
    match role {
        "pelvis" | "torso" | "head" | "hand" | "foot" => {
            Some(&["form_extent_x", "form_extent_y", "form_extent_z"])
        }
        "neck" | "upper_arm" | "forearm" | "thigh" | "shin" => Some(&["form_radius"]),
        "tail_root" | "tail_tip" => Some(&["form_start_radius", "form_end_radius"]),
        _ => None,
    }
}

fn dimension_value(
    dimensions: &PreparedAuthoredDimensions,
    address: &AddressKey,
    role: &str,
) -> u32 {
    *dimensions
        .values
        .get(&(address.clone(), role.to_owned()))
        .expect("required authored dimension was validated before shape construction")
}

fn scale(value: u32, factor: u32, profile_id: &'static str) -> Result<u32, InspectionError> {
    let scaled = u64::from(value)
        .checked_mul(u64::from(factor))
        .ok_or(InspectionError::Core(
            ProvisionalFormPreviewError::InvalidProfileValue { profile_id, value },
        ))?
        / 1_000;
    let scaled = u32::try_from(scaled).map_err(|_| {
        InspectionError::Core(ProvisionalFormPreviewError::InvalidProfileValue {
            profile_id,
            value: u32::MAX,
        })
    })?;
    if scaled == 0 || scaled > MAX_PROVISIONAL_PERMILLE {
        return Err(InspectionError::Core(
            ProvisionalFormPreviewError::InvalidProfileValue {
                profile_id,
                value: scaled,
            },
        ));
    }
    Ok(scaled)
}

fn extents(
    profile_id: &'static str,
    address: &AddressKey,
    dimensions: &PreparedAuthoredDimensions,
) -> Result<[u32; 3], InspectionError> {
    let base = [
        dimension_value(dimensions, address, "form_extent_x"),
        dimension_value(dimensions, address, "form_extent_y"),
        dimension_value(dimensions, address, "form_extent_z"),
    ];
    let role = address.role();
    let factors = match profile_id {
        "neutral-v0" => [1_000, 1_000, 1_000],
        "broad-soft-v0" if matches!(role, "pelvis" | "torso" | "head") => [1_200, 1_000, 1_150],
        "broad-soft-v0" if matches!(role, "hand" | "foot") => [1_150, 1_000, 1_150],
        "broad-soft-v0" => [1_000; 3],
        "lean-readable-v0" => [800, 1_000, 800],
        "depth-forward-v0" if matches!(role, "torso" | "head" | "foot") => [1_000, 1_000, 1_300],
        "depth-forward-v0" => [1_000; 3],
        _ => [1_000; 3],
    };
    let mut result = [0; 3];
    for index in 0..3 {
        result[index] = scale(base[index], factors[index], profile_id)?;
    }
    Ok(result)
}

fn radius(
    profile_id: &'static str,
    address: &AddressKey,
    dimensions: &PreparedAuthoredDimensions,
) -> Result<u32, InspectionError> {
    let factor = match profile_id {
        "broad-soft-v0" => 1_150,
        "lean-readable-v0" => 800,
        _ => 1_000,
    };
    scale(
        dimension_value(dimensions, address, "form_radius"),
        factor,
        profile_id,
    )
}

fn taper_radii(
    profile_id: &'static str,
    address: &AddressKey,
    dimensions: &PreparedAuthoredDimensions,
) -> Result<(u32, u32), InspectionError> {
    let (start_factor, end_factor) = match profile_id {
        "broad-soft-v0" => (1_150, 1_150),
        "lean-readable-v0" => (800, 800),
        _ => (1_000, 1_000),
    };
    Ok((
        scale(
            dimension_value(dimensions, address, "form_start_radius"),
            start_factor,
            profile_id,
        )?,
        scale(
            dimension_value(dimensions, address, "form_end_radius"),
            end_factor,
            profile_id,
        )?,
    ))
}

fn map_source_preparation_error(error: SourcePreparationError) -> ProvisionalFormPreviewError {
    let message = error.to_string();
    match error {
        SourcePreparationError::Admission(admission) => {
            let status = match admission.status {
                AdmissionStatus::InvalidSource => ProvisionalSourceFailureKind::InvalidSource,
                AdmissionStatus::Unsupported => ProvisionalSourceFailureKind::Unsupported,
                AdmissionStatus::ResourceLimit => ProvisionalSourceFailureKind::ResourceLimit,
                AdmissionStatus::InternalFailure | AdmissionStatus::Success => {
                    ProvisionalSourceFailureKind::InternalFailure
                }
            };
            ProvisionalFormPreviewError::SourcePreparation {
                status,
                processing_complete: admission.processing_complete,
                diagnostics_complete: admission.diagnostics_complete,
                message,
            }
        }
        SourcePreparationError::Structural(_)
        | SourcePreparationError::Basis(_)
        | SourcePreparationError::Numeric { .. } => {
            ProvisionalFormPreviewError::SourcePreparation {
                status: ProvisionalSourceFailureKind::InvalidSource,
                processing_complete: true,
                diagnostics_complete: true,
                message,
            }
        }
        SourcePreparationError::Invariant { .. } => {
            ProvisionalFormPreviewError::SourcePreparation {
                status: ProvisionalSourceFailureKind::InternalFailure,
                processing_complete: false,
                diagnostics_complete: false,
                message,
            }
        }
    }
}

fn exact_translation_value(
    translation: creature_kernel_core::reference_placement::ExactTranslation,
) -> Value {
    let [x, y, z] = translation.components();
    json!([x, y, z])
}

fn placement_source_name(source: PlacementSource) -> &'static str {
    match source {
        PlacementSource::AuthoredRoot => "authored-root",
        PlacementSource::AuthoredContainment => "authored-containment",
        PlacementSource::AuthoredAttachment => "authored-attachment",
    }
}

fn failure(error: InspectionError) -> CliResult {
    let (stage, status, code, processing_complete, diagnostics_complete) = match &error {
        InspectionError::Core(ProvisionalFormPreviewError::SourcePreparation {
            status,
            processing_complete,
            diagnostics_complete,
            ..
        }) => (
            "source-preparation",
            source_status_name(*status),
            "ck.cli.provisional-form.source-preparation",
            *processing_complete,
            *diagnostics_complete,
        ),
        InspectionError::Core(ProvisionalFormPreviewError::DeclaredDependenciesUnsupported {
            ..
        }) => (
            "provisional-form",
            "unsupported",
            "ck.cli.provisional-form.dependencies",
            true,
            true,
        ),
        InspectionError::Core(ProvisionalFormPreviewError::ReferencePlacement {
            kind,
            processing_complete,
            diagnostics_complete,
            ..
        }) => (
            "reference-placement",
            placement_status_name(*kind),
            "ck.cli.provisional-form.reference-placement",
            *processing_complete,
            *diagnostics_complete,
        ),
        InspectionError::Core(ProvisionalFormPreviewError::NoNonzeroReferenceEdge {
            kind,
            processing_complete,
            diagnostics_complete,
        }) => (
            "reference-scale",
            placement_status_name(*kind),
            "ck.cli.provisional-form.no-reference-edge",
            *processing_complete,
            *diagnostics_complete,
        ),
        InspectionError::Core(ProvisionalFormPreviewError::ReferenceEdgeArithmeticOverflow {
            kind,
            processing_complete,
            diagnostics_complete,
            ..
        }) => (
            "reference-scale",
            placement_status_name(*kind),
            "ck.cli.provisional-form.reference-arithmetic",
            *processing_complete,
            *diagnostics_complete,
        ),
        InspectionError::Core(ProvisionalFormPreviewError::UnsupportedPartRole { .. }) => (
            "descriptor",
            "unsupported",
            "ck.cli.provisional-form.unsupported-role",
            true,
            true,
        ),
        InspectionError::Core(ProvisionalFormPreviewError::ZeroLengthSegment { .. }) => (
            "descriptor",
            "invalid-source",
            "ck.cli.provisional-form.zero-length-segment",
            true,
            true,
        ),
        InspectionError::Core(ProvisionalFormPreviewError::MissingSegmentParent { .. }) => (
            "descriptor",
            "invalid-source",
            "ck.cli.provisional-form.missing-segment-parent",
            true,
            true,
        ),
        InspectionError::Core(ProvisionalFormPreviewError::MissingSegmentChild { .. }) => (
            "descriptor",
            "invalid-source",
            "ck.cli.provisional-form.missing-segment-child",
            true,
            true,
        ),
        InspectionError::Core(ProvisionalFormPreviewError::AmbiguousSegmentChild { .. }) => (
            "descriptor",
            "invalid-source",
            "ck.cli.provisional-form.ambiguous-segment-child",
            true,
            true,
        ),
        InspectionError::Core(ProvisionalFormPreviewError::InvalidProfileValue { .. }) => (
            "descriptor",
            "internal-failure",
            "ck.cli.provisional-form.profile-value",
            false,
            false,
        ),
        InspectionError::MissingAuthoredDimension { .. }
        | InspectionError::InvalidAuthoredDimension { .. } => (
            "dimensions",
            "invalid-source",
            "ck.cli.provisional-form.authored-dimension",
            true,
            true,
        ),
    };
    let diagnostic = cli_diagnostic(code, error.to_string());
    let mut output = base_output(stage);
    output.insert("status".to_owned(), Value::String(status.to_owned()));
    output.insert(
        "processing_complete".to_owned(),
        Value::Bool(processing_complete),
    );
    output.insert(
        "diagnostics_complete".to_owned(),
        Value::Bool(diagnostics_complete),
    );
    output.insert("diagnostics".to_owned(), json!([diagnostic.clone()]));
    output.insert("primary_diagnostic".to_owned(), diagnostic);
    result(Value::Object(output))
}

fn source_status_name(status: ProvisionalSourceFailureKind) -> &'static str {
    match status {
        ProvisionalSourceFailureKind::InvalidSource => "invalid-source",
        ProvisionalSourceFailureKind::Unsupported => "unsupported",
        ProvisionalSourceFailureKind::ResourceLimit => "resource-limit",
        ProvisionalSourceFailureKind::InternalFailure => "internal-failure",
    }
}

fn placement_status_name(kind: ProvisionalPlacementFailureKind) -> &'static str {
    match kind {
        ProvisionalPlacementFailureKind::Unavailable => "unavailable",
        ProvisionalPlacementFailureKind::InvalidSource => "invalid-source",
        ProvisionalPlacementFailureKind::InternalFailure => "internal-failure",
    }
}

fn result(value: Value) -> CliResult {
    let exit_code = if value.get("status") == Some(&Value::String("success".to_owned())) {
        0
    } else {
        1
    };
    CliResult {
        json: creature_kernel_core::provisional_json::to_string(&value).unwrap_or_else(|_| {
            r#"{"format":"creature-kernel.provisional-form-preview.v5","operation":"inspect-provisional-form","status":"internal-failure","stage":"output","diagnostics":[{"code":"ck.cli.provisional-form.output-serialization","message":"could not serialize provisional form inspection result"}]}"#.to_owned()
        }),
        exit_code,
    }
}

fn base_output(stage: &str) -> Map<String, Value> {
    Map::from_iter([
        ("format".to_owned(), Value::String(FORMAT.to_owned())),
        ("operation".to_owned(), Value::String(OPERATION.to_owned())),
        ("stage".to_owned(), Value::String(stage.to_owned())),
    ])
}

fn usage_error(message: &str) -> Value {
    let mut output = base_output("usage");
    output.insert("status".to_owned(), Value::String("usage-error".to_owned()));
    output.insert("processing_complete".to_owned(), Value::Bool(false));
    output.insert("diagnostics_complete".to_owned(), Value::Bool(true));
    let diagnostic = cli_diagnostic("ck.cli.provisional-form.usage", message);
    output.insert("diagnostics".to_owned(), json!([diagnostic.clone()]));
    output.insert("primary_diagnostic".to_owned(), diagnostic);
    Value::Object(output)
}

fn input_error(message: String) -> Value {
    let mut output = base_output("input");
    output.insert(
        "status".to_owned(),
        Value::String("input-failure".to_owned()),
    );
    output.insert("processing_complete".to_owned(), Value::Bool(false));
    output.insert("diagnostics_complete".to_owned(), Value::Bool(true));
    let diagnostic = cli_diagnostic("ck.cli.provisional-form.input-read", message);
    output.insert("diagnostics".to_owned(), json!([diagnostic.clone()]));
    output.insert("primary_diagnostic".to_owned(), diagnostic);
    Value::Object(output)
}

fn cli_diagnostic(code: &str, message: impl Into<String>) -> Value {
    json!({
        "code": code,
        "message": message.into(),
        "instance_path": Value::Null,
        "schema_path": Value::Null,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use creature_kernel_core::provisional_json::{Value, json};

    fn example() -> Vec<u8> {
        include_bytes!(
            "../../../examples/body-documents/stylized-digitigrade-biped-authored-form.json"
        )
        .to_vec()
    }

    fn parsed(output: &CliResult) -> Value {
        creature_kernel_core::provisional_json::from_str(&output.json).expect("JSON output")
    }

    fn document() -> Value {
        creature_kernel_core::provisional_json::from_slice(&example()).expect("example JSON")
    }

    fn bytes(value: Value) -> Vec<u8> {
        creature_kernel_core::provisional_json::to_vec(&value).expect("JSON bytes")
    }

    #[test]
    fn command_help_and_usage_are_structured_and_non_partial() {
        let help = run_cli([OPERATION, "--help"]);
        assert_eq!(help.exit_code, 0);
        let help = parsed(&help);
        assert_eq!(help["format"], FORMAT);
        assert_eq!(help["operation"], OPERATION);
        assert_eq!(help["status"], "success");
        assert!(help["help"]["usage"].is_string());
        assert!(
            help["help"]["usage"]
                .as_str()
                .unwrap()
                .contains("(use '-' for stdin)")
        );

        let usage = run_cli([OPERATION]);
        assert_eq!(usage.exit_code, 1);
        let usage = parsed(&usage);
        assert_eq!(usage["status"], "usage-error");
        assert!(usage.get("variants").is_none());
        assert!(usage.get("source").is_none());
    }

    #[test]
    fn biped_success_has_four_named_variants_and_eighteen_descriptors() {
        let output = inspect_source(&example());
        assert_eq!(output.exit_code, 0);
        let value = parsed(&output);
        assert_eq!(
            value["format"],
            "creature-kernel.provisional-form-preview.v5"
        );
        assert_eq!(value["operation"], OPERATION);
        assert_eq!(value["status"], "success");
        let variants = value["variants"].as_array().unwrap();
        assert_eq!(variants.len(), 4);
        let ids: Vec<_> = variants
            .iter()
            .map(|variant| variant["id"].as_str().unwrap())
            .collect();
        assert_eq!(
            ids,
            [
                "neutral-v0",
                "broad-soft-v0",
                "lean-readable-v0",
                "depth-forward-v0"
            ]
        );
        for variant in variants {
            assert_eq!(variant["descriptors"].as_array().unwrap().len(), 18);
            for descriptor in variant["descriptors"].as_array().unwrap() {
                assert_eq!(
                    descriptor["provenance"]["source"],
                    creature_kernel_core::provisional_form_preview::DISPLAY_PROVENANCE
                );
                assert_eq!(
                    descriptor["provenance"]["shape_basis"],
                    SHAPE_BASIS_PROVENANCE
                );
                assert!(descriptor["reference_point"].is_array());
                assert!(descriptor["shape"]["name"].is_string());
            }
        }
        assert_eq!(value["authored_dimensions"].as_array().unwrap().len(), 34);
        assert!(
            value["limitations"]
                .as_str()
                .unwrap()
                .contains("no production geometry")
        );
    }

    #[test]
    fn authored_dimension_inventory_and_descriptor_consumption_are_complete() {
        let value = parsed(&inspect_source(&example()));
        let dimensions = value["authored_dimensions"].as_array().unwrap();
        assert_eq!(dimensions.len(), 34);
        let keys = dimensions
            .iter()
            .map(|dimension| {
                (
                    dimension["owner"]["namespace"].as_str().unwrap().to_owned(),
                    dimension["owner"]["anchors"]
                        .as_array()
                        .unwrap()
                        .iter()
                        .map(|anchor| anchor.as_str().unwrap().to_owned())
                        .collect::<Vec<_>>(),
                    dimension["owner"]["role"].as_str().unwrap().to_owned(),
                    dimension["role"].as_str().unwrap().to_owned(),
                )
            })
            .collect::<Vec<_>>();
        assert!(keys.windows(2).all(|pair| pair[0] < pair[1]));
        assert!(dimensions.iter().all(|dimension| {
            dimension["value_permille"]
                .as_u64()
                .is_some_and(|value| value > 0 && value <= u64::from(MAX_PROVISIONAL_PERMILLE))
                && dimension["provenance"]["source"] == AUTHORED_DIMENSION_PROVENANCE
                && dimension["provenance"]["document"] == "stylized_digitigrade_biped_authored_form"
                && dimension["provenance"]["namespace"] == "main"
        }));

        for variant in value["variants"].as_array().unwrap() {
            for descriptor in variant["descriptors"].as_array().unwrap() {
                let expected =
                    authored_dimension_roles(descriptor["address"]["role"].as_str().unwrap())
                        .expect("descriptor role has authored controls");
                assert_eq!(
                    descriptor["dimension_roles"],
                    Value::Array(expected.iter().map(|role| json!(role)).collect())
                );
                for role in expected {
                    assert!(dimensions.iter().any(|dimension| {
                        dimension["owner"] == descriptor["address"] && dimension["role"] == *role
                    }));
                }
            }
        }
    }

    #[test]
    fn missing_fractional_nonpositive_and_oversized_controls_fail_closed() {
        let mut missing = document();
        missing["body"]["dimensions"]
            .as_array_mut()
            .unwrap()
            .remove(0);
        let missing = parsed(&inspect_source(&bytes(missing)));
        assert_eq!(missing["status"], "invalid-source");
        assert_eq!(missing["stage"], "dimensions");
        assert_eq!(
            missing["diagnostics"][0]["code"],
            "ck.cli.provisional-form.authored-dimension"
        );

        for invalid in [json!(1.5), json!(0), json!(-1), json!(5_001)] {
            let mut document = document();
            document["body"]["dimensions"].as_array_mut().unwrap()[0]["value"] = invalid;
            let result = parsed(&inspect_source(&bytes(document)));
            assert_eq!(result["status"], "invalid-source");
            assert_eq!(result["stage"], "dimensions");
            assert_eq!(
                result["diagnostics"][0]["code"],
                "ck.cli.provisional-form.authored-dimension"
            );
        }
    }

    #[test]
    fn one_authored_dimension_changes_only_its_shape_basis_in_all_variants() {
        let original = parsed(&inspect_source(&example()));
        let mut changed_source = document();
        let torso_x = changed_source["body"]["dimensions"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|dimension| {
                dimension["owner"]["role"] == "torso" && dimension["role"] == "form_extent_x"
            })
            .expect("torso x control");
        torso_x["value"] = json!(1_750);
        let changed = parsed(&inspect_source(&bytes(changed_source)));

        for (original_variant, changed_variant) in original["variants"]
            .as_array()
            .unwrap()
            .iter()
            .zip(changed["variants"].as_array().unwrap())
        {
            for (original_descriptor, changed_descriptor) in original_variant["descriptors"]
                .as_array()
                .unwrap()
                .iter()
                .zip(changed_variant["descriptors"].as_array().unwrap())
            {
                assert_eq!(
                    original_descriptor["address"],
                    changed_descriptor["address"]
                );
                if original_descriptor["address"]["role"] == "torso" {
                    assert_ne!(original_descriptor["shape"], changed_descriptor["shape"]);
                } else {
                    assert_eq!(original_descriptor["shape"], changed_descriptor["shape"]);
                }
            }
        }
    }

    #[test]
    fn repeated_and_permuted_sources_are_byte_deterministic() {
        let first = inspect_source(&example());
        let second = inspect_source(&example());
        assert_eq!(first.json, second.json);

        let mut value: Value =
            creature_kernel_core::provisional_json::from_slice(&example()).unwrap();
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
        ] {
            value["body"][collection].as_array_mut().unwrap().reverse();
        }
        let reordered = creature_kernel_core::provisional_json::to_vec(&value).unwrap();
        assert_eq!(first.json, inspect_source(&reordered).json);
    }

    #[test]
    fn admission_and_restricted_placement_statuses_are_not_flattened() {
        let unsupported = include_bytes!(
            "../../../fixtures/body-documents/readiness-2/unsupported-revision.json"
        );
        let unsupported = parsed(&inspect_source(unsupported));
        assert_eq!(unsupported["status"], "unsupported");
        assert_eq!(unsupported["processing_complete"], true);
        assert!(unsupported.get("variants").is_none());

        let oversized =
            vec![b' '; creature_kernel_core::body_document::ORDINARY_MAX_SOURCE_BYTES + 1];
        let oversized = parsed(&inspect_source(&oversized));
        assert_eq!(oversized["status"], "resource-limit");
        assert_eq!(oversized["processing_complete"], false);
        assert!(oversized.get("reference_scale").is_none());

        let mut noncanonical =
            creature_kernel_core::provisional_json::from_slice::<Value>(&example()).unwrap();
        noncanonical["basis"]["length_unit"] = json!("centimetre");
        let noncanonical = parsed(&inspect_source(
            &creature_kernel_core::provisional_json::to_vec(&noncanonical).unwrap(),
        ));
        assert_eq!(noncanonical["status"], "unavailable");
        assert_eq!(noncanonical["processing_complete"], true);
        assert!(noncanonical.get("variants").is_none());

        let mut nonidentity_rotation =
            creature_kernel_core::provisional_json::from_slice::<Value>(&example()).unwrap();
        let neck = nonidentity_rotation["body"]["parts"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|part| part["address"]["role"] == "neck")
            .unwrap();
        neck["placement"]["rotation_xyzw"] = json!([0, 0, 1, 0]);
        let nonidentity_rotation = parsed(&inspect_source(
            &creature_kernel_core::provisional_json::to_vec(&nonidentity_rotation).unwrap(),
        ));
        assert_eq!(nonidentity_rotation["status"], "unavailable");
        assert_eq!(nonidentity_rotation["processing_complete"], true);
        assert!(nonidentity_rotation.get("variants").is_none());

        let mut disagreement =
            creature_kernel_core::provisional_json::from_slice::<Value>(&example()).unwrap();
        let host = disagreement["body"]["sockets"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|socket| socket["address"]["anchors"] == json!([]))
            .unwrap();
        host["interface_frame"]["translation"] = json!([0, 0, 0]);
        let disagreement = parsed(&inspect_source(
            &creature_kernel_core::provisional_json::to_vec(&disagreement).unwrap(),
        ));
        assert_eq!(disagreement["status"], "invalid-source");
        assert_eq!(disagreement["processing_complete"], true);
        assert!(disagreement.get("reference_scale").is_none());
    }

    #[test]
    fn malformed_source_and_missing_input_have_no_preview_payload() {
        let malformed = inspect_source(b"{");
        assert_eq!(malformed.exit_code, 1);
        let malformed = parsed(&malformed);
        assert!(malformed.get("variants").is_none());
        assert!(malformed.get("reference_scale").is_none());
        assert!(
            malformed["diagnostics"][0]["code"]
                .as_str()
                .unwrap()
                .starts_with("ck.cli.provisional-form.")
        );

        let missing = run_cli([OPERATION, "--input", "definitely-not-present.json"]);
        assert_eq!(missing.exit_code, 1);
        let missing = parsed(&missing);
        assert_eq!(missing["status"], "input-failure");
        assert!(missing.get("variants").is_none());
    }
}
