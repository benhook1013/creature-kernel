//! Provisional developer-facing source-preparation inspection adapter.
//!
//! This command exposes the bounded, single-source preparation projection as
//! a human-inspection envelope.  It deliberately keeps the structural graph
//! projection shared with `inspect-structure`; the prepared values are an
//! additional debug view and are not canonical serialization or resolver
//! output.

use crate::structural_inspection;
use creature_kernel_core::body_document::{Diagnostic, ResourceProfile, Status};
use creature_kernel_core::body_graph::OwnerRoleKey;
use creature_kernel_core::frame::{self, RigidTransform, SignedAxis};
use creature_kernel_core::numeric::NormalizedBinary64;
use creature_kernel_core::provisional_json::{Map, Value, json};
use creature_kernel_core::semantic_address::AddressKey;
use creature_kernel_core::source_preparation::{
    PositionComponent, PreparedSingleSource, SourceNumericCause, SourceNumericLocation,
    SourcePreparationError, SourceTransformComponent, prepare_single_source,
};
use creature_kernel_core::structural_validation::StructuralDiagnostic;
use std::path::Path;

const FORMAT: &str = "creature-kernel.provisional-source-preparation-inspection.v1";
const LIMITATIONS: &str = "Provisional source preparation only: no dependency resolver or snapshot, no basis or unit application, no quaternion semantics, no dependency or module expansion, no geometry, and no runtime claim.";

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
            "usage: creature-kernel inspect-prepared-source --input <path> (use '-' for stdin)",
        ));
    };

    let source = match structural_inspection::read_input(input) {
        Ok(source) => source,
        Err(error) => return result(input_error(error.to_string())),
    };

    inspect_source(&source)
}

fn help_response(arguments: &[String]) -> Option<Value> {
    let (operation, usage, description) = match arguments {
        [command, flag]
            if command == "inspect-prepared-source" && (flag == "--help" || flag == "-h") =>
        {
            (
                "inspect-prepared-source",
                "creature-kernel inspect-prepared-source --input <path>",
                "Inspect admitted source values after bounded preparation and emit a provisional debug projection.",
            )
        }
        _ => return None,
    };

    let mut output = base_output("help");
    output.insert("operation".to_owned(), Value::String(operation.to_owned()));
    output.insert("status".to_owned(), Value::String("success".to_owned()));
    output.insert("processing_complete".to_owned(), Value::Bool(true));
    output.insert("diagnostics_complete".to_owned(), Value::Bool(true));
    output.insert("diagnostics".to_owned(), Value::Array(Vec::new()));
    output.insert(
        "help".to_owned(),
        json!({
            "usage": usage,
            "description": description,
            "options": [
                {"flag": "--input <path>", "description": "Read a body document from a file (use '-' for stdin)."},
                {"flag": "--help", "description": "Show this structured help response."}
            ]
        }),
    );
    Some(Value::Object(output))
}

fn parse_input_path(arguments: &[String]) -> Option<&Path> {
    if arguments.first().map(String::as_str) != Some("inspect-prepared-source") {
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
    match prepare_single_source(source, ResourceProfile::ORDINARY) {
        Ok(prepared) => success(prepared),
        Err(error) => failure(error),
    }
}

fn success(prepared: PreparedSingleSource) -> CliResult {
    let graph = prepared.graph();
    let graph_projection = structural_inspection::graph_projection(graph);
    let mut output = base_output("source-preparation");
    output.insert("status".to_owned(), Value::String("success".to_owned()));
    output.insert("processing_complete".to_owned(), Value::Bool(true));
    output.insert("diagnostics_complete".to_owned(), Value::Bool(true));
    output.insert("diagnostics".to_owned(), Value::Array(Vec::new()));
    output.insert("source".to_owned(), graph_projection["source"].clone());
    output.insert("contract".to_owned(), json!(graph.contract()));
    output.insert("profiles".to_owned(), json!(graph.profiles()));
    output.insert("graph".to_owned(), graph_projection);
    output.insert(
        "prepared".to_owned(),
        json!({
            "basis": basis_projection(prepared.basis()),
            "counts": prepared_counts(&prepared),
            "numeric_values": numeric_values(&prepared),
        }),
    );
    output.insert(
        "limitations".to_owned(),
        Value::String(LIMITATIONS.to_owned()),
    );
    result(Value::Object(output))
}

fn failure(error: SourcePreparationError) -> CliResult {
    match error {
        SourcePreparationError::Admission(admission) => {
            let mut output = base_output("admission");
            let missing_document = admission.status == Status::Success;
            output.insert(
                "status".to_owned(),
                Value::String(
                    if missing_document {
                        "internal-failure"
                    } else {
                        status_name(admission.status)
                    }
                    .to_owned(),
                ),
            );
            output.insert(
                "processing_complete".to_owned(),
                Value::Bool(admission.processing_complete),
            );
            output.insert(
                "diagnostics_complete".to_owned(),
                Value::Bool(admission.diagnostics_complete),
            );
            output.insert(
                "effective_diagnostic_profile_id".to_owned(),
                Value::String(admission.effective_diagnostic_profile_id.to_owned()),
            );
            output.insert(
                "effective_resource_profile_id".to_owned(),
                Value::String(admission.effective_resource_profile_id.to_owned()),
            );
            let diagnostics = if missing_document {
                vec![cli_diagnostic(
                    "ck.cli.missing-admitted-document",
                    "admission reported success without a document",
                )]
            } else {
                admission
                    .diagnostics
                    .iter()
                    .map(admission_diagnostic)
                    .collect()
            };
            output.insert("diagnostics".to_owned(), Value::Array(diagnostics));
            if missing_document {
                output.insert(
                    "primary_diagnostic".to_owned(),
                    cli_diagnostic(
                        "ck.cli.missing-admitted-document",
                        "admission reported success without a document",
                    ),
                );
            } else if let Some(primary) = admission.primary_diagnostic.as_ref() {
                output.insert(
                    "primary_diagnostic".to_owned(),
                    admission_diagnostic(primary),
                );
            }
            result(Value::Object(output))
        }
        SourcePreparationError::Structural(error) => {
            let mut output = base_output("source-preparation");
            output.insert(
                "status".to_owned(),
                Value::String("invalid-source".to_owned()),
            );
            output.insert("processing_complete".to_owned(), Value::Bool(true));
            output.insert("diagnostics_complete".to_owned(), Value::Bool(true));
            output.insert(
                "diagnostics".to_owned(),
                Value::Array(
                    error
                        .diagnostics
                        .iter()
                        .map(structural_diagnostic)
                        .collect(),
                ),
            );
            if let Some(primary) = error.diagnostics.first() {
                output.insert(
                    "primary_diagnostic".to_owned(),
                    structural_diagnostic(primary),
                );
            }
            result(Value::Object(output))
        }
        SourcePreparationError::Basis(error) => {
            let mut output = base_output("source-preparation");
            output.insert(
                "status".to_owned(),
                Value::String("invalid-source".to_owned()),
            );
            output.insert("processing_complete".to_owned(), Value::Bool(true));
            output.insert("diagnostics_complete".to_owned(), Value::Bool(true));
            let diagnostic = basis_diagnostic(error);
            output.insert("diagnostics".to_owned(), json!([diagnostic.clone()]));
            output.insert("primary_diagnostic".to_owned(), diagnostic);
            result(Value::Object(output))
        }
        SourcePreparationError::Numeric { location, cause } => {
            let mut output = base_output("source-preparation");
            output.insert(
                "status".to_owned(),
                Value::String("invalid-source".to_owned()),
            );
            output.insert("processing_complete".to_owned(), Value::Bool(true));
            output.insert("diagnostics_complete".to_owned(), Value::Bool(true));
            let diagnostic = numeric_diagnostic(&location, cause);
            output.insert("diagnostics".to_owned(), json!([diagnostic.clone()]));
            output.insert("primary_diagnostic".to_owned(), diagnostic);
            result(Value::Object(output))
        }
        SourcePreparationError::Invariant { collection, error } => {
            let mut output = base_output("source-preparation");
            output.insert(
                "status".to_owned(),
                Value::String("internal-failure".to_owned()),
            );
            output.insert("processing_complete".to_owned(), Value::Bool(true));
            output.insert("diagnostics_complete".to_owned(), Value::Bool(true));
            let diagnostic = cli_diagnostic(
                "ck.cli.source-preparation-invariant",
                format!("{collection} structural invariant failed: {error}"),
            );
            output.insert("diagnostics".to_owned(), json!([diagnostic.clone()]));
            output.insert("primary_diagnostic".to_owned(), diagnostic);
            result(Value::Object(output))
        }
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
            r#"{"format":"creature-kernel.provisional-source-preparation-inspection.v1","operation":"inspect-prepared-source","status":"internal-failure","stage":"output","diagnostics":[{"code":"ck.cli.output-serialization","message":"could not serialize inspection result"}]}"#.to_owned()
        }),
        exit_code,
    }
}

fn base_output(stage: &str) -> Map<String, Value> {
    Map::from_iter([
        ("format".to_owned(), Value::String(FORMAT.to_owned())),
        (
            "operation".to_owned(),
            Value::String("inspect-prepared-source".to_owned()),
        ),
        ("stage".to_owned(), Value::String(stage.to_owned())),
    ])
}

fn usage_error(message: &str) -> Value {
    let mut output = base_output("usage");
    output.insert("status".to_owned(), Value::String("usage-error".to_owned()));
    output.insert("processing_complete".to_owned(), Value::Bool(false));
    output.insert("diagnostics_complete".to_owned(), Value::Bool(true));
    let diagnostic = cli_diagnostic("ck.cli.usage", message);
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
    let diagnostic = cli_diagnostic("ck.cli.input-read", message);
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

fn admission_diagnostic(diagnostic: &Diagnostic) -> Value {
    json!({
        "code": diagnostic.code,
        "message": diagnostic.message,
        "instance_path": diagnostic.instance_path,
        "schema_path": diagnostic.schema_path,
    })
}

fn structural_diagnostic(diagnostic: &StructuralDiagnostic) -> Value {
    json!({
        "category": diagnostic.category.as_str(),
        "code": diagnostic.code,
        "address": diagnostic.address.as_ref().map(structural_inspection::address_key_value),
        "role": diagnostic.role,
        "detail": diagnostic.detail,
    })
}

fn basis_diagnostic(error: frame::BasisError) -> Value {
    json!({
        "category": "basis",
        "code": "ck.frame.basis-collinear",
        "message": error.to_string(),
        "instance_path": "/basis/up,/basis/forward",
        "cause": "collinear-axes",
    })
}

fn numeric_diagnostic(location: &SourceNumericLocation, cause: SourceNumericCause) -> Value {
    let (cause_kind, cause_message, details) = match cause {
        SourceNumericCause::MaterializedTokenTooLong {
            actual_bytes,
            limit_bytes,
        } => (
            "materialized-token-too-long",
            format!(
                "materialized number token is {actual_bytes} bytes; limit is {limit_bytes} bytes"
            ),
            json!({"actual_bytes": actual_bytes, "limit_bytes": limit_bytes}),
        ),
        SourceNumericCause::DecimalConversion(error) => (
            "decimal-conversion",
            error.to_string(),
            json!({"error": format!("{error:?}")}),
        ),
    };
    json!({
        "category": "numeric",
        "code": "ck.frame.numeric-preparation",
        "message": format!("numeric preparation failed: {cause_message}"),
        "location": numeric_location(location),
        "cause": {"kind": cause_kind, "message": cause_message, "details": details},
    })
}

fn numeric_location(location: &SourceNumericLocation) -> Value {
    match location {
        SourceNumericLocation::PartPlacement { address, component } => {
            transform_location("parts", address, "placement", *component)
        }
        SourceNumericLocation::JointProximal { address, component } => {
            transform_location("joints", address, "proximal_frame", *component)
        }
        SourceNumericLocation::JointDistal { address, component } => {
            transform_location("joints", address, "distal_frame", *component)
        }
        SourceNumericLocation::SocketInterface { address, component } => {
            transform_location("sockets", address, "interface_frame", *component)
        }
        SourceNumericLocation::AttachmentOffset { address, component } => {
            transform_location("attachments", address, "offset", *component)
        }
        SourceNumericLocation::LandmarkPosition {
            owner_role,
            component,
        } => json!({
            "group": "landmarks",
            "owner_role": owner_role_value(owner_role),
            "field": "position",
            "component": position_component_name(*component),
        }),
        SourceNumericLocation::DimensionValue { owner_role } => json!({
            "group": "dimensions",
            "owner_role": owner_role_value(owner_role),
            "field": "value",
            "component": "scalar",
        }),
        SourceNumericLocation::NamedFrame {
            owner_role,
            component,
        } => json!({
            "group": "frames",
            "owner_role": owner_role_value(owner_role),
            "field": "transform",
            "component": transform_component_name(*component),
        }),
    }
}

fn transform_location(
    group: &str,
    address: &AddressKey,
    field: &str,
    component: SourceTransformComponent,
) -> Value {
    json!({
        "group": group,
        "address": structural_inspection::address_key_value(address),
        "field": field,
        "component": transform_component_name(component),
    })
}

fn basis_projection(basis: frame::SourceBasis) -> Value {
    json!({
        "length_unit": length_unit_name(basis.length_unit()),
        "handedness": handedness_name(basis.handedness()),
        "up": signed_axis_name(basis.up()),
        "forward": signed_axis_name(basis.forward()),
        "source_for_canonical": basis
            .mapping()
            .source_for_canonical()
            .into_iter()
            .map(signed_axis_name)
            .collect::<Vec<_>>(),
    })
}

fn prepared_counts(prepared: &PreparedSingleSource) -> Value {
    json!({
        "parts": prepared.parts().len(),
        "joints": prepared.joints().len(),
        "sockets": prepared.sockets().len(),
        "attachments": prepared.attachments().len(),
        "landmarks": prepared.landmarks().len(),
        "dimensions": prepared.dimensions().len(),
        "frames": prepared.frames().len(),
    })
}

fn numeric_values(prepared: &PreparedSingleSource) -> Vec<Value> {
    let mut rows = Vec::new();
    for (address, transform) in prepared.parts() {
        push_transform_rows(
            &mut rows,
            "parts",
            Some(address),
            "placement",
            *transform,
            None,
        );
    }
    for (address, frames) in prepared.joints() {
        push_transform_rows(
            &mut rows,
            "joints",
            Some(address),
            "proximal_frame",
            frames.proximal(),
            None,
        );
        push_transform_rows(
            &mut rows,
            "joints",
            Some(address),
            "distal_frame",
            frames.distal(),
            None,
        );
    }
    for (address, transform) in prepared.sockets() {
        push_transform_rows(
            &mut rows,
            "sockets",
            Some(address),
            "interface_frame",
            *transform,
            None,
        );
    }
    for (address, transform) in prepared.attachments() {
        push_transform_rows(
            &mut rows,
            "attachments",
            Some(address),
            "offset",
            *transform,
            None,
        );
    }
    for (owner_role, landmark) in prepared.landmarks() {
        for (component, value) in landmark.position().components().into_iter().enumerate() {
            let component = match component {
                0 => PositionComponent::X,
                1 => PositionComponent::Y,
                2 => PositionComponent::Z,
                _ => unreachable!(),
            };
            rows.push(numeric_row(
                "landmarks",
                Some(owner_role),
                None,
                "position",
                position_component_name(component),
                value,
                Some(landmark.frame()),
            ));
        }
    }
    for (owner_role, value) in prepared.dimensions() {
        rows.push(numeric_row(
            "dimensions",
            Some(owner_role),
            None,
            "value",
            "scalar",
            *value,
            None,
        ));
    }
    for (owner_role, transform) in prepared.frames() {
        push_transform_rows(
            &mut rows,
            "frames",
            None,
            "transform",
            *transform,
            Some(owner_role),
        );
    }
    rows
}

fn push_transform_rows(
    rows: &mut Vec<Value>,
    group: &str,
    address: Option<&AddressKey>,
    field: &str,
    transform: RigidTransform,
    owner_role: Option<&OwnerRoleKey>,
) {
    for (component, value) in ["x", "y", "z"]
        .into_iter()
        .zip(transform.translation().components())
    {
        rows.push(numeric_row(
            group,
            owner_role,
            address,
            field,
            &format!("translation.{component}"),
            value,
            None,
        ));
    }
    for (component, value) in ["x", "y", "z", "w"]
        .into_iter()
        .zip(transform.rotation().components())
    {
        rows.push(numeric_row(
            group,
            owner_role,
            address,
            field,
            &format!("rotation.{component}"),
            value,
            None,
        ));
    }
}

fn numeric_row(
    group: &str,
    owner_role: Option<&OwnerRoleKey>,
    address: Option<&AddressKey>,
    field: &str,
    component: &str,
    value: NormalizedBinary64,
    frame: Option<&OwnerRoleKey>,
) -> Value {
    let mut row = Map::from_iter([
        ("group".to_owned(), Value::String(group.to_owned())),
        ("field".to_owned(), Value::String(field.to_owned())),
        ("component".to_owned(), Value::String(component.to_owned())),
        (
            "display_value".to_owned(),
            Value::String(value.as_f64().to_string()),
        ),
        (
            "binary64_bits".to_owned(),
            Value::String(format!("{:016x}", value.to_bits())),
        ),
    ]);
    if let Some(address) = address {
        row.insert(
            "address".to_owned(),
            structural_inspection::address_key_value(address),
        );
    }
    if let Some(owner_role) = owner_role {
        row.insert("owner_role".to_owned(), owner_role_value(owner_role));
    }
    if let Some(frame) = frame {
        row.insert("frame".to_owned(), owner_role_value(frame));
    }
    Value::Object(row)
}

fn owner_role_value(owner_role: &OwnerRoleKey) -> Value {
    json!({
        "owner": structural_inspection::address_key_value(owner_role.owner()),
        "role": owner_role.role(),
    })
}

fn transform_component_name(component: SourceTransformComponent) -> &'static str {
    match component {
        SourceTransformComponent::TranslationX => "translation.x",
        SourceTransformComponent::TranslationY => "translation.y",
        SourceTransformComponent::TranslationZ => "translation.z",
        SourceTransformComponent::RotationX => "rotation.x",
        SourceTransformComponent::RotationY => "rotation.y",
        SourceTransformComponent::RotationZ => "rotation.z",
        SourceTransformComponent::RotationW => "rotation.w",
    }
}

fn position_component_name(component: PositionComponent) -> &'static str {
    match component {
        PositionComponent::X => "x",
        PositionComponent::Y => "y",
        PositionComponent::Z => "z",
    }
}

fn length_unit_name(unit: frame::LengthUnit) -> &'static str {
    match unit {
        frame::LengthUnit::Millimetre => "millimetre",
        frame::LengthUnit::Centimetre => "centimetre",
        frame::LengthUnit::Metre => "metre",
    }
}

fn handedness_name(handedness: frame::Handedness) -> &'static str {
    match handedness {
        frame::Handedness::Left => "left",
        frame::Handedness::Right => "right",
    }
}

fn signed_axis_name(axis: SignedAxis) -> &'static str {
    match axis {
        SignedAxis::PositiveX => "+x",
        SignedAxis::NegativeX => "-x",
        SignedAxis::PositiveY => "+y",
        SignedAxis::NegativeY => "-y",
        SignedAxis::PositiveZ => "+z",
        SignedAxis::NegativeZ => "-z",
    }
}

fn status_name(status: Status) -> &'static str {
    match status {
        Status::Success => "success",
        Status::InvalidSource => "invalid-source",
        Status::Unsupported => "unsupported",
        Status::ResourceLimit => "resource-limit",
        Status::InternalFailure => "internal-failure",
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use creature_kernel_core::provisional_json;
    use creature_kernel_core::provisional_json as serde_json;

    fn biped() -> Vec<u8> {
        include_bytes!("../../../examples/body-documents/stylized-digitigrade-biped.json").to_vec()
    }

    fn minimal_envelope() -> Vec<u8> {
        include_bytes!("../../../fixtures/body-documents/readiness-2/minimal-valid-envelope.json")
            .to_vec()
    }

    fn value(source: &[u8]) -> Value {
        provisional_json::from_str(&inspect_source(source).json).unwrap()
    }

    #[test]
    fn checked_in_biped_emits_prepared_counts_basis_and_stable_bits() {
        let output = inspect_source(&biped());
        assert_eq!(output.exit_code, 0);
        let value = provisional_json::from_str::<Value>(&output.json).unwrap();
        assert_eq!(value["format"], FORMAT);
        assert_eq!(value["operation"], "inspect-prepared-source");
        assert_eq!(value["stage"], "source-preparation");
        assert_eq!(value["status"], "success");
        assert_eq!(value["prepared"]["basis"]["length_unit"], "metre");
        assert_eq!(value["prepared"]["basis"]["handedness"], "right");
        assert_eq!(value["prepared"]["basis"]["up"], "+y");
        assert_eq!(value["prepared"]["basis"]["forward"], "+z");
        assert_eq!(
            value["prepared"]["basis"]["source_for_canonical"],
            json!(["+x", "+y", "+z"])
        );
        assert_eq!(value["prepared"]["counts"]["parts"], 18);
        assert_eq!(value["prepared"]["counts"]["joints"], 17);
        assert_eq!(value["prepared"]["counts"]["sockets"], 2);
        assert_eq!(value["prepared"]["counts"]["attachments"], 1);
        assert_eq!(value["prepared"]["counts"]["landmarks"], 0);
        assert_eq!(value["prepared"]["counts"]["dimensions"], 0);
        assert_eq!(value["prepared"]["counts"]["frames"], 0);
        let rows = value["prepared"]["numeric_values"].as_array().unwrap();
        assert_eq!(rows.len(), 385);
        let pelvis_x = rows
            .iter()
            .find(|row| {
                row["group"] == "parts"
                    && row["address"]["role"] == "pelvis"
                    && row["field"] == "placement"
                    && row["component"] == "translation.x"
            })
            .unwrap();
        assert_eq!(pelvis_x["display_value"], "0");
        assert_eq!(pelvis_x["binary64_bits"], "0000000000000000");
        assert!(
            value["limitations"]
                .as_str()
                .unwrap()
                .contains("no geometry")
        );
    }

    #[test]
    fn source_collection_permutations_are_byte_identical() {
        let mut source: serde_json::Value = serde_json::from_slice(&biped()).unwrap();
        let mut reversed = source.clone();
        for collection in ["parts", "joints", "sockets", "attachments"] {
            reversed["body"][collection]
                .as_array_mut()
                .unwrap()
                .reverse();
        }
        source["body"]["parts"].as_array_mut().unwrap().reverse();
        source["body"]["parts"].as_array_mut().unwrap().reverse();
        let first = inspect_source(&serde_json::to_vec(&source).unwrap());
        let second = inspect_source(&serde_json::to_vec(&reversed).unwrap());
        assert_eq!(first.exit_code, 0);
        assert_eq!(second.exit_code, 0);
        assert_eq!(first.json, second.json);
    }

    #[test]
    fn preparation_errors_are_bounded_and_do_not_emit_partial_payloads() {
        let admission = value(br#"{}"#);
        assert_eq!(admission["status"], "invalid-source");
        assert!(admission.get("prepared").is_none());
        assert!(admission.get("graph").is_none());

        let structural = value(&minimal_envelope());
        assert_eq!(structural["status"], "invalid-source");
        assert!(structural["diagnostics"][0]["category"].is_string());
        assert!(structural.get("prepared").is_none());

        let mut basis: serde_json::Value = serde_json::from_slice(&biped()).unwrap();
        basis["basis"]["forward"] = serde_json::Value::String("-y".to_owned());
        let basis = value(&serde_json::to_vec(&basis).unwrap());
        assert_eq!(basis["status"], "invalid-source");
        assert_eq!(basis["diagnostics"][0]["category"], "basis");
        assert!(basis.get("prepared").is_none());

        let mut numeric: serde_json::Value = serde_json::from_slice(&biped()).unwrap();
        numeric["body"]["parts"][0]["placement"]["translation"][0] =
            serde_json::from_str("1.7976931348623159e308").unwrap();
        let numeric = value(&serde_json::to_vec(&numeric).unwrap());
        assert_eq!(numeric["status"], "invalid-source");
        assert_eq!(numeric["diagnostics"][0]["category"], "numeric");
        assert!(numeric["diagnostics"][0]["location"].is_object());
        assert!(numeric.get("prepared").is_none());
    }

    #[test]
    fn help_usage_and_missing_input_are_structured() {
        let help = run_cli(["inspect-prepared-source", "--help"]);
        assert_eq!(help.exit_code, 0);
        let help = provisional_json::from_str::<Value>(&help.json).unwrap();
        assert_eq!(help["status"], "success");
        assert!(help["help"].is_object());
        let usage = run_cli(["inspect-prepared-source"]);
        assert_eq!(usage.exit_code, 1);
        let usage = provisional_json::from_str::<Value>(&usage.json).unwrap();
        assert_eq!(usage["status"], "usage-error");
        assert_eq!(usage["primary_diagnostic"], usage["diagnostics"][0]);
        let missing = run_cli([
            "inspect-prepared-source",
            "--input",
            "/definitely/not/a/body.json",
        ]);
        assert_eq!(missing.exit_code, 1);
        let missing = provisional_json::from_str::<Value>(&missing.json).unwrap();
        assert_eq!(missing["status"], "input-failure");
        assert_eq!(missing["primary_diagnostic"], missing["diagnostics"][0]);
    }
}
