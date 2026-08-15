//! Provisional CLI adapter for the display-only filled-form descriptor slice.
//!
//! This command is intentionally a developer inspection operation.  Its
//! payload contains exact integer source points and fixed profile tuning; it
//! does not publish geometry, mesh, SDF, anatomy, runtime, or Readiness 3
//! output.

use creature_kernel_core::body_document::ResourceProfile;
use creature_kernel_core::provisional_form_preview::{
    ProvisionalFormPreview, ProvisionalFormPreviewError, ProvisionalPlacementFailureKind,
    ProvisionalShape, ProvisionalSourceFailureKind, build_provisional_form_preview,
};
use creature_kernel_core::provisional_json::{Map, Value, json};
use creature_kernel_core::reference_placement::PlacementSource;
use std::path::Path;

const FORMAT: &str = "creature-kernel.provisional-form-preview.v3";
const OPERATION: &str = "inspect-provisional-form";
const LIMITATIONS: &str = "Provisional display-only filled-form descriptors from the restricted single-source exact Part placement projection; no production geometry, mesh, SDF, topology, collision, rig, skin, anatomy, Joint-frame interpretation, authored dimensions, general units or rotations, dependency resolution, canonical snapshot/serialization, runtime claim, or Readiness activation. Descriptors are not graph Parts.";

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
        Ok(preview) => success(preview),
        Err(error) => failure(error),
    }
}

fn success(preview: ProvisionalFormPreview) -> CliResult {
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
        "variants": preview.variants().iter().map(variant_value).collect::<Vec<_>>(),
        "limitations": LIMITATIONS,
    });
    result(output)
}

fn variant_value(
    variant: &creature_kernel_core::provisional_form_preview::ProvisionalFormVariant,
) -> Value {
    json!({
        "id": variant.id(),
        "profile_id": variant.provenance().profile_id(),
        "provenance": {
            "source": variant.provenance().source(),
            "resource_profile_id": variant.provenance().resource_profile_id(),
        },
        "descriptors": variant.descriptors().iter().map(descriptor_value).collect::<Vec<_>>(),
    })
}

fn descriptor_value(
    descriptor: &creature_kernel_core::provisional_form_preview::ProvisionalPartDescriptor,
) -> Value {
    json!({
        "descriptor_kind": "display-only-form-descriptor",
        "address": crate::structural_inspection::address_key_value(descriptor.address()),
        "parent": descriptor.parent().map(crate::structural_inspection::address_key_value).unwrap_or(Value::Null),
        "placement_source": placement_source_name(descriptor.placement_source()),
        "reference_point": exact_translation_value(descriptor.reference_point()),
        "profile_id": descriptor.provenance().profile_id(),
        "source": descriptor.provenance().source(),
        "provenance": {
            "source": descriptor.provenance().source(),
            "resource_profile_id": descriptor.provenance().resource_profile_id(),
        },
        "shape": shape_value(descriptor.shape()),
    })
}

fn shape_value(shape: &ProvisionalShape) -> Value {
    match shape {
        ProvisionalShape::Ellipsoid {
            center,
            axis_extents_permille,
        } => json!({
            "name": "ellipsoid",
            "center": exact_translation_value(*center),
            "axis_extents_permille": axis_extents_permille,
        }),
        ProvisionalShape::Capsule {
            from,
            to,
            radius_permille,
        } => json!({
            "name": "capsule",
            "from": exact_translation_value(*from),
            "to": exact_translation_value(*to),
            "radius_permille": radius_permille,
        }),
        ProvisionalShape::TaperedSegment {
            from,
            to,
            start_radius_permille,
            end_radius_permille,
        } => json!({
            "name": "tapered-segment",
            "from": exact_translation_value(*from),
            "to": exact_translation_value(*to),
            "start_radius_permille": start_radius_permille,
            "end_radius_permille": end_radius_permille,
        }),
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

fn failure(error: ProvisionalFormPreviewError) -> CliResult {
    let (stage, status, code, processing_complete, diagnostics_complete) = match &error {
        ProvisionalFormPreviewError::SourcePreparation {
            status,
            processing_complete,
            diagnostics_complete,
            ..
        } => (
            "source-preparation",
            source_status_name(*status),
            "ck.cli.provisional-form.source-preparation",
            *processing_complete,
            *diagnostics_complete,
        ),
        ProvisionalFormPreviewError::DeclaredDependenciesUnsupported { .. } => (
            "provisional-form",
            "unsupported",
            "ck.cli.provisional-form.dependencies",
            true,
            true,
        ),
        ProvisionalFormPreviewError::ReferencePlacement {
            kind,
            processing_complete,
            diagnostics_complete,
            ..
        } => (
            "reference-placement",
            placement_status_name(*kind),
            "ck.cli.provisional-form.reference-placement",
            *processing_complete,
            *diagnostics_complete,
        ),
        ProvisionalFormPreviewError::NoNonzeroReferenceEdge {
            kind,
            processing_complete,
            diagnostics_complete,
        } => (
            "reference-scale",
            placement_status_name(*kind),
            "ck.cli.provisional-form.no-reference-edge",
            *processing_complete,
            *diagnostics_complete,
        ),
        ProvisionalFormPreviewError::ReferenceEdgeArithmeticOverflow {
            kind,
            processing_complete,
            diagnostics_complete,
            ..
        } => (
            "reference-scale",
            placement_status_name(*kind),
            "ck.cli.provisional-form.reference-arithmetic",
            *processing_complete,
            *diagnostics_complete,
        ),
        ProvisionalFormPreviewError::UnsupportedPartRole { .. } => (
            "descriptor",
            "unsupported",
            "ck.cli.provisional-form.unsupported-role",
            true,
            true,
        ),
        ProvisionalFormPreviewError::ZeroLengthSegment { .. } => (
            "descriptor",
            "invalid-source",
            "ck.cli.provisional-form.zero-length-segment",
            true,
            true,
        ),
        ProvisionalFormPreviewError::MissingSegmentParent { .. } => (
            "descriptor",
            "invalid-source",
            "ck.cli.provisional-form.missing-segment-parent",
            true,
            true,
        ),
        ProvisionalFormPreviewError::MissingSegmentChild { .. } => (
            "descriptor",
            "invalid-source",
            "ck.cli.provisional-form.missing-segment-child",
            true,
            true,
        ),
        ProvisionalFormPreviewError::AmbiguousSegmentChild { .. } => (
            "descriptor",
            "invalid-source",
            "ck.cli.provisional-form.ambiguous-segment-child",
            true,
            true,
        ),
        ProvisionalFormPreviewError::InvalidProfileValue { .. } => (
            "descriptor",
            "internal-failure",
            "ck.cli.provisional-form.profile-value",
            false,
            false,
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
            r#"{"format":"creature-kernel.provisional-form-preview.v3","operation":"inspect-provisional-form","status":"internal-failure","stage":"output","diagnostics":[{"code":"ck.cli.provisional-form.output-serialization","message":"could not serialize provisional form inspection result"}]}"#.to_owned()
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
        include_bytes!("../../../examples/body-documents/stylized-digitigrade-biped.json").to_vec()
    }

    fn parsed(output: &CliResult) -> Value {
        creature_kernel_core::provisional_json::from_str(&output.json).expect("JSON output")
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
            "creature-kernel.provisional-form-preview.v3"
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
                assert!(descriptor["reference_point"].is_array());
                assert!(descriptor["shape"]["name"].is_string());
            }
        }
        assert!(
            value["limitations"]
                .as_str()
                .unwrap()
                .contains("no production geometry")
        );
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
