//! Provisional CLI inspection for the engine-neutral runtime-input handoff.
//!
//! The command is deliberately a small adapter over the existing single-source
//! preparation operation and the provisional ordered handoff.  Its output is a
//! bounded debug envelope, not a runtime-input or package serialization.

use creature_kernel_core::body_document::{Diagnostic, ResourceProfile, Status};
use creature_kernel_core::frame::{self, SignedAxis};
use creature_kernel_core::provisional_json::{Map, Value, json};
use creature_kernel_core::provisional_runtime_input::{
    ProvisionalRuntimeAvatarInput, ProvisionalRuntimeInputError, handoff_provisional_runtime_input,
};
use creature_kernel_core::source_preparation::{
    PreparedSingleSource, SourcePreparationError, prepare_single_source,
};
use creature_kernel_core::structural_validation::StructuralDiagnostic;
use std::collections::BTreeSet;
use std::path::PathBuf;

const FORMAT: &str = "creature-kernel.provisional-runtime-input-inspection.v1";
const OPERATION: &str = "inspect-runtime-input";
const USAGE: &str =
    "usage: creature-kernel inspect-runtime-input (--instance <id> --source <path>)+";
/// Provisional CLI instrumentation/resource-hygiene bound, not a core/package contract.
const MAX_INSTANCE_SOURCE_PAIRS: usize = 64;

/// Serialized result and process status for one CLI invocation.
#[derive(Debug, PartialEq)]
pub(crate) struct CliResult {
    pub json: String,
    pub exit_code: i32,
}

#[derive(Debug, PartialEq, Eq)]
struct InstanceSourceSpec {
    instance_id: String,
    source: PathBuf,
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

    let specs = match parse_specs(&arguments) {
        Ok(specs) => specs,
        Err(message) => return result(usage_error(message)),
    };

    let mut instances = Vec::with_capacity(specs.len());
    for spec in specs {
        let source = match crate::structural_inspection::read_input(&spec.source) {
            Ok(source) => source,
            Err(error) => return result(input_error(&spec.instance_id, error.to_string())),
        };
        let prepared = match prepare_single_source(&source, ResourceProfile::ORDINARY) {
            Ok(prepared) => prepared,
            Err(error) => return result(preparation_failure(&spec.instance_id, error)),
        };
        match ProvisionalRuntimeAvatarInput::new(spec.instance_id, prepared) {
            Ok(instance) => instances.push(instance),
            Err(error) => return result(handoff_failure(error)),
        }
    }

    finish_handoff(instances)
}

fn help_response(arguments: &[String]) -> Option<Value> {
    if !matches!(
        arguments,
        [command, flag]
            if command == OPERATION && (*flag == "--help" || *flag == "-h")
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
            "usage": USAGE,
            "description": "Prepare repeated explicit source instances and inspect the provisional ordered runtime-input handoff (provisional CLI cap: 64 pairs per invocation; not a core/package contract).",
            "options": [
                {"flag": "--instance <id>", "description": "Set one non-empty instance ID; repeat each instance/source pair in caller order."},
                {"flag": "--source <path>", "description": "Read that instance's body document from a file (use '-' for stdin)."},
                {"flag": "--help", "description": "Show this structured help response."}
            ]
        }),
    );
    Some(Value::Object(output))
}

fn parse_specs(arguments: &[String]) -> Result<Vec<InstanceSourceSpec>, String> {
    if arguments.first().map(String::as_str) != Some(OPERATION) {
        return Err(USAGE.to_owned());
    }

    let mut specs = Vec::new();
    let mut instance_ids = BTreeSet::new();
    let mut stdin_source_seen = false;
    let mut index = 1;
    while index < arguments.len() {
        if arguments[index] != "--instance" {
            return Err(format!(
                "{USAGE}: expected --instance at argument {}",
                index + 1
            ));
        }
        let instance_id = arguments
            .get(index + 1)
            .ok_or_else(|| format!("{USAGE}: missing instance ID after --instance"))?;
        if instance_id.is_empty() || instance_id.starts_with('-') {
            return Err(format!(
                "{USAGE}: instance ID must be a non-empty value that does not begin with '-'"
            ));
        }
        if !instance_ids.insert(instance_id.clone()) {
            return Err(format!("{USAGE}: duplicate instance ID {instance_id:?}"));
        }
        index += 2;

        if arguments.get(index).map(String::as_str) != Some("--source") {
            return Err(format!(
                "{USAGE}: expected --source after instance ID {instance_id:?}"
            ));
        }
        let source = arguments
            .get(index + 1)
            .ok_or_else(|| format!("{USAGE}: missing source path after --source"))?;
        if source.is_empty() || (source.starts_with('-') && source != "-") {
            return Err(format!(
                "{USAGE}: source path must be a non-empty value or '-' for stdin"
            ));
        }
        if source == "-" {
            if stdin_source_seen {
                return Err(format!("{USAGE}: --source - may be specified at most once"));
            }
            stdin_source_seen = true;
        }
        if specs.len() >= MAX_INSTANCE_SOURCE_PAIRS {
            return Err(format!(
                "{USAGE}: at most {MAX_INSTANCE_SOURCE_PAIRS} instance/source pairs are allowed"
            ));
        }
        specs.push(InstanceSourceSpec {
            instance_id: instance_id.clone(),
            source: PathBuf::from(source),
        });
        index += 2;
    }

    if specs.is_empty() {
        return Err(format!(
            "{USAGE}: at least one instance/source pair is required"
        ));
    }
    Ok(specs)
}

/// Inspect already-acquired source bytes in the supplied order.
#[cfg(test)]
fn inspect_sources(sources: Vec<(String, Vec<u8>)>) -> CliResult {
    let mut instances = Vec::with_capacity(sources.len());
    for (instance_id, source) in sources {
        let prepared = match prepare_single_source(&source, ResourceProfile::ORDINARY) {
            Ok(prepared) => prepared,
            Err(error) => return result(preparation_failure(&instance_id, error)),
        };
        match ProvisionalRuntimeAvatarInput::new(instance_id, prepared) {
            Ok(instance) => instances.push(instance),
            Err(error) => return result(handoff_failure(error)),
        }
    }
    finish_handoff(instances)
}

fn finish_handoff(instances: Vec<ProvisionalRuntimeAvatarInput>) -> CliResult {
    match handoff_provisional_runtime_input(instances) {
        Ok(handoff) => success(handoff.instances()),
        Err(error) => result(handoff_failure(error)),
    }
}

fn success(instances: &[ProvisionalRuntimeAvatarInput]) -> CliResult {
    let output = json!({
        "format": FORMAT,
        "operation": OPERATION,
        "stage": "runtime-input",
        "status": "success",
        "processing_complete": true,
        "diagnostics_complete": true,
        "diagnostics": [],
        "instances": instances.iter().map(instance_projection).collect::<Vec<_>>(),
    });
    result(output)
}

fn instance_projection(instance: &ProvisionalRuntimeAvatarInput) -> Value {
    let prepared = instance.prepared_source();
    let graph = prepared.graph();
    json!({
        "instance_id": instance.instance_id(),
        "source": {
            "document": graph.source().document.as_str(),
            "namespace": graph.source().namespace.as_str(),
        },
        "prepared": {
            "basis": basis_projection(prepared.basis()),
            "counts": prepared_counts(prepared),
        },
        "structural": {
            "counts": structural_counts(graph),
        },
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

fn structural_counts(graph: &creature_kernel_core::body_graph::StructuralBodyGraph) -> Value {
    json!({
        "modules": graph.modules().len(),
        "parts": graph.parts().len(),
        "joints": graph.joints().len(),
        "sockets": graph.sockets().len(),
        "attachments": graph.attachments().len(),
        "landmarks": graph.landmarks().len(),
        "dimensions": graph.dimensions().len(),
        "frames": graph.frames().len(),
        "regions": graph.regions().len(),
        "capabilities": graph.capabilities().len(),
        "fields": graph.fields().len(),
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

fn preparation_failure(instance_id: &str, error: SourcePreparationError) -> Value {
    let (status, processing_complete, diagnostics_complete, diagnostics, primary) = match error {
        SourcePreparationError::Admission(admission) => {
            let missing_document = admission.status == Status::Success;
            let status = if missing_document {
                "internal-failure"
            } else {
                status_name(admission.status)
            };
            let missing_document_diagnostic = || {
                cli_diagnostic(
                    "ck.cli.missing-admitted-document",
                    "source admission did not provide a usable document",
                )
            };
            let diagnostics = if missing_document {
                vec![missing_document_diagnostic()]
            } else {
                admission
                    .diagnostics
                    .iter()
                    .map(admission_diagnostic)
                    .collect()
            };
            let primary = if missing_document {
                Some(missing_document_diagnostic())
            } else {
                admission
                    .primary_diagnostic
                    .as_ref()
                    .map(admission_diagnostic)
            };
            (
                status,
                admission.processing_complete,
                admission.diagnostics_complete,
                diagnostics,
                primary,
            )
        }
        SourcePreparationError::Structural(error) => {
            let diagnostics: Vec<Value> = error
                .diagnostics
                .iter()
                .map(structural_diagnostic)
                .collect();
            let primary = diagnostics.first().cloned().unwrap_or_else(|| {
                cli_diagnostic(
                    "ck.cli.source-preparation",
                    "source preparation failed without a diagnostic",
                )
            });
            ("invalid-source", true, true, diagnostics, Some(primary))
        }
        SourcePreparationError::Basis(error) => {
            let diagnostic = cli_diagnostic("ck.cli.source-preparation.basis", error.to_string());
            (
                "invalid-source",
                true,
                true,
                vec![diagnostic.clone()],
                Some(diagnostic),
            )
        }
        SourcePreparationError::Numeric { location, cause } => {
            let diagnostic = cli_diagnostic(
                "ck.cli.source-preparation.numeric",
                format!("numeric preparation failed at {location:?}: {cause:?}"),
            );
            (
                "invalid-source",
                true,
                true,
                vec![diagnostic.clone()],
                Some(diagnostic),
            )
        }
        SourcePreparationError::Invariant { collection, error } => {
            let diagnostic = cli_diagnostic(
                "ck.cli.source-preparation.invariant",
                format!("{collection} structural invariant failed: {error}"),
            );
            (
                "internal-failure",
                true,
                true,
                vec![diagnostic.clone()],
                Some(diagnostic),
            )
        }
    };

    let mut output = base_output("source-preparation");
    output.insert("status".to_owned(), Value::String(status.to_owned()));
    output.insert(
        "processing_complete".to_owned(),
        Value::Bool(processing_complete),
    );
    output.insert(
        "diagnostics_complete".to_owned(),
        Value::Bool(diagnostics_complete),
    );
    output.insert(
        "instance_id".to_owned(),
        Value::String(instance_id.to_owned()),
    );
    output.insert("diagnostics".to_owned(), Value::Array(diagnostics));
    if let Some(primary) = primary {
        output.insert("primary_diagnostic".to_owned(), primary);
    }
    Value::Object(output)
}

fn handoff_failure(error: ProvisionalRuntimeInputError) -> Value {
    let diagnostic = cli_diagnostic("ck.cli.runtime-input", error.to_string());
    let mut output = base_output("runtime-input");
    output.insert("status".to_owned(), Value::String("usage-error".to_owned()));
    output.insert("processing_complete".to_owned(), Value::Bool(false));
    output.insert("diagnostics_complete".to_owned(), Value::Bool(true));
    output.insert("diagnostics".to_owned(), json!([diagnostic.clone()]));
    output.insert("primary_diagnostic".to_owned(), diagnostic);
    Value::Object(output)
}

fn usage_error(message: impl Into<String>) -> Value {
    let diagnostic = cli_diagnostic("ck.cli.usage", message);
    let mut output = base_output("usage");
    output.insert("status".to_owned(), Value::String("usage-error".to_owned()));
    output.insert("processing_complete".to_owned(), Value::Bool(false));
    output.insert("diagnostics_complete".to_owned(), Value::Bool(true));
    output.insert("diagnostics".to_owned(), json!([diagnostic.clone()]));
    output.insert("primary_diagnostic".to_owned(), diagnostic);
    Value::Object(output)
}

fn input_error(instance_id: &str, message: String) -> Value {
    let diagnostic = cli_diagnostic("ck.cli.input-read", message);
    let mut output = base_output("input");
    output.insert(
        "status".to_owned(),
        Value::String("input-failure".to_owned()),
    );
    output.insert("processing_complete".to_owned(), Value::Bool(false));
    output.insert("diagnostics_complete".to_owned(), Value::Bool(true));
    output.insert(
        "instance_id".to_owned(),
        Value::String(instance_id.to_owned()),
    );
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
        "address": diagnostic.address.as_ref().map(crate::structural_inspection::address_key_value),
        "role": diagnostic.role,
        "detail": diagnostic.detail,
    })
}

fn result(value: Value) -> CliResult {
    let exit_code = if value.get("status") == Some(&Value::String("success".to_owned())) {
        0
    } else {
        1
    };
    CliResult {
        json: creature_kernel_core::provisional_json::to_string(&value).unwrap_or_else(|_| {
            format!(
                r#"{{"format":"{FORMAT}","operation":"{OPERATION}","status":"internal-failure","stage":"output","diagnostics":[{{"code":"ck.cli.output-serialization","message":"could not serialize inspection result"}}]}}"#
            )
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
    use creature_kernel_core::body_document::AdmissionResult;
    use creature_kernel_core::provisional_json;

    fn biped() -> Vec<u8> {
        include_bytes!("../../../examples/body-documents/stylized-digitigrade-biped.json").to_vec()
    }

    fn authored_biped() -> Vec<u8> {
        include_bytes!(
            "../../../examples/body-documents/stylized-digitigrade-biped-authored-form.json"
        )
        .to_vec()
    }

    fn value(result: &CliResult) -> Value {
        provisional_json::from_str(&result.json).expect("CLI result is JSON")
    }

    fn repeated_pair_arguments(count: usize) -> Vec<String> {
        let mut arguments = vec![OPERATION.to_owned()];
        for index in 0..count {
            arguments.extend([
                "--instance".to_owned(),
                format!("instance-{index}"),
                "--source".to_owned(),
                format!("source-{index}.json"),
            ]);
        }
        arguments
    }

    #[test]
    fn help_describes_repeated_ordered_pairs() {
        let result = run_cli([OPERATION, "--help"]);
        assert_eq!(result.exit_code, 0);
        let value = value(&result);
        assert_eq!(value["operation"], OPERATION);
        assert_eq!(value["status"], "success");
        assert_eq!(value["help"]["usage"], USAGE);
        assert!(
            value["help"]["description"]
                .as_str()
                .unwrap()
                .contains("ordered")
        );
        assert!(
            value["help"]["description"]
                .as_str()
                .unwrap()
                .contains("provisional CLI cap: 64 pairs")
        );
    }

    #[test]
    fn usage_accepts_the_inclusive_instance_source_pair_cap() {
        let specs = parse_specs(&repeated_pair_arguments(MAX_INSTANCE_SOURCE_PAIRS))
            .expect("the inclusive operation cap remains accepted");
        assert_eq!(specs.len(), MAX_INSTANCE_SOURCE_PAIRS);
        assert_eq!(specs[0].instance_id, "instance-0");
        assert_eq!(
            specs[MAX_INSTANCE_SOURCE_PAIRS - 1].instance_id,
            format!("instance-{}", MAX_INSTANCE_SOURCE_PAIRS - 1)
        );
    }

    #[test]
    fn usage_rejects_an_instance_source_pair_over_cap_before_input_reads() {
        let result = run_cli(repeated_pair_arguments(MAX_INSTANCE_SOURCE_PAIRS + 1));
        assert_eq!(result.exit_code, 1);
        let value = value(&result);
        assert_eq!(value["status"], "usage-error");
        assert_eq!(value["stage"], "usage");
        assert!(
            value["primary_diagnostic"]["message"]
                .as_str()
                .unwrap()
                .contains("at most 64 instance/source pairs")
        );
    }

    #[test]
    fn usage_rejects_missing_malformed_and_duplicate_ids() {
        for arguments in [
            vec![OPERATION.to_owned()],
            vec![OPERATION.to_owned(), "--instance".to_owned()],
            vec![
                OPERATION.to_owned(),
                "--instance".to_owned(),
                "one".to_owned(),
                "--source".to_owned(),
            ],
            vec![
                OPERATION.to_owned(),
                "--instance".to_owned(),
                "--source".to_owned(),
                "source.json".to_owned(),
            ],
            vec![
                OPERATION.to_owned(),
                "--instance".to_owned(),
                "same".to_owned(),
                "--source".to_owned(),
                "one.json".to_owned(),
                "--instance".to_owned(),
                "same".to_owned(),
                "--source".to_owned(),
                "two.json".to_owned(),
            ],
        ] {
            let result = run_cli(arguments);
            assert_eq!(result.exit_code, 1);
            let value = value(&result);
            assert_eq!(value["status"], "usage-error");
            assert_eq!(value["primary_diagnostic"], value["diagnostics"][0]);
        }
    }

    #[test]
    fn usage_rejects_repeated_stdin_before_reading_any_input() {
        let result = run_cli([
            OPERATION,
            "--instance",
            "first",
            "--source",
            "-",
            "--instance",
            "second",
            "--source",
            "-",
        ]);
        assert_eq!(result.exit_code, 1);
        let value = value(&result);
        assert_eq!(value["status"], "usage-error");
        assert_eq!(value["stage"], "usage");
        assert!(
            value["primary_diagnostic"]["message"]
                .as_str()
                .unwrap()
                .contains("may be specified at most once")
        );
        assert_ne!(value["status"], "success");
        assert!(value.get("instances").is_none());
    }

    #[test]
    fn usage_accepts_one_stdin_source() {
        let specs = parse_specs(&[
            OPERATION.to_owned(),
            "--instance".to_owned(),
            "stdin-instance".to_owned(),
            "--source".to_owned(),
            "-".to_owned(),
        ])
        .expect("one stdin source remains supported");
        assert_eq!(specs.len(), 1);
        assert_eq!(specs[0].instance_id, "stdin-instance");
        assert_eq!(specs[0].source, PathBuf::from("-"));
    }

    #[test]
    fn success_emits_only_bounded_ordered_instance_summaries() {
        let result = inspect_sources(vec![
            ("right-instance".to_owned(), authored_biped()),
            ("left-instance".to_owned(), biped()),
        ]);
        assert_eq!(result.exit_code, 0);
        let value = value(&result);
        assert_eq!(value["format"], FORMAT);
        assert_eq!(value["operation"], OPERATION);
        assert_eq!(value["stage"], "runtime-input");
        assert_eq!(value["status"], "success");
        let instances = value["instances"].as_array().unwrap();
        assert_eq!(instances[0]["instance_id"], "right-instance");
        assert_eq!(
            instances[0]["source"]["document"],
            "stylized_digitigrade_biped_authored_form"
        );
        assert_eq!(instances[0]["source"]["namespace"], "main");
        assert_eq!(instances[1]["instance_id"], "left-instance");
        assert_eq!(
            instances[1]["source"]["document"],
            "stylized_digitigrade_biped"
        );
        assert_eq!(instances[0]["prepared"]["counts"]["parts"], 18);
        assert_eq!(instances[0]["structural"]["counts"]["parts"], 18);
        assert_eq!(instances[0]["prepared"]["basis"]["up"], "+y");
        for forbidden in [
            "profile_id",
            "candidate_hash",
            "artifacts",
            "package",
            "godot",
            "host",
            "adapter",
            "r3",
            "geometry",
            "runtime",
        ] {
            assert!(
                value.get(forbidden).is_none(),
                "unexpected top-level {forbidden}"
            );
            assert!(
                instances[0].get(forbidden).is_none(),
                "unexpected instance {forbidden}"
            );
        }
    }

    #[test]
    fn source_preparation_failure_is_fail_closed_without_partial_instances() {
        let result = inspect_sources(vec![
            ("good-instance".to_owned(), biped()),
            ("bad-instance".to_owned(), b"{".to_vec()),
        ]);
        assert_eq!(result.exit_code, 1);
        let value = value(&result);
        assert_eq!(value["status"], "invalid-source");
        assert_eq!(value["stage"], "source-preparation");
        assert_eq!(value["instance_id"], "bad-instance");
        assert!(value.get("instances").is_none());
        assert_eq!(value["primary_diagnostic"], value["diagnostics"][0]);
    }

    #[test]
    fn resource_limit_preserves_incomplete_admission_processing() {
        let result = inspect_sources(vec![(
            "limited-instance".to_owned(),
            vec![b' '; creature_kernel_core::body_document::ORDINARY_MAX_SOURCE_BYTES + 1],
        )]);
        assert_eq!(result.exit_code, 1);
        let value = value(&result);
        assert_eq!(value["status"], "resource-limit");
        assert_eq!(value["processing_complete"], false);
        assert_eq!(value["diagnostics_complete"], true);
        assert_eq!(
            value["primary_diagnostic"]["code"],
            creature_kernel_core::body_document::CODE_RESOURCE_SOURCE_BYTES
        );
    }

    #[test]
    fn truncated_admission_diagnostics_preserve_independent_primary() {
        let retained = Diagnostic {
            code: "ck.test.retained",
            message: "retained diagnostic".to_owned(),
            instance_path: Some("/body/retained".to_owned()),
            schema_path: Some("/schema/retained".to_owned()),
        };
        let primary = Diagnostic {
            code: "ck.test.primary",
            message: "normative primary diagnostic".to_owned(),
            instance_path: Some("/body/primary".to_owned()),
            schema_path: Some("/schema/primary".to_owned()),
        };
        let admission = AdmissionResult {
            status: Status::InvalidSource,
            processing_complete: true,
            diagnostics_complete: false,
            effective_diagnostic_profile_id:
                creature_kernel_core::body_document::DIAGNOSTIC_PROFILE_ID,
            effective_resource_profile_id:
                creature_kernel_core::body_document::ORDINARY_RESOURCE_PROFILE_ID,
            primary_diagnostic: Some(primary),
            diagnostics: vec![retained],
            document: None,
        };

        let value = preparation_failure(
            "truncated-instance",
            SourcePreparationError::Admission(Box::new(admission)),
        );
        assert_eq!(value["status"], "invalid-source");
        assert_eq!(value["processing_complete"], true);
        assert_eq!(value["diagnostics_complete"], false);
        assert_eq!(value["diagnostics"].as_array().unwrap().len(), 1);
        assert_eq!(value["diagnostics"][0]["code"], "ck.test.retained");
        assert_eq!(value["primary_diagnostic"]["code"], "ck.test.primary");
        assert_ne!(value["primary_diagnostic"], value["diagnostics"][0]);
    }

    #[test]
    fn repeated_handoff_is_byte_deterministic_and_preserves_caller_order() {
        let sources = vec![
            ("zeta".to_owned(), authored_biped()),
            ("alpha".to_owned(), biped()),
        ];
        let first = inspect_sources(sources.clone());
        let second = inspect_sources(sources);
        assert_eq!(first.exit_code, 0);
        assert_eq!(first.json, second.json);
        let value = value(&first);
        assert_eq!(value["instances"][0]["instance_id"], "zeta");
        assert_eq!(value["instances"][1]["instance_id"], "alpha");
    }

    #[test]
    fn handoff_duplicate_is_fail_closed_even_for_direct_adapter_input() {
        let result = inspect_sources(vec![
            ("same".to_owned(), biped()),
            ("same".to_owned(), authored_biped()),
        ]);
        assert_eq!(result.exit_code, 1);
        let value = value(&result);
        assert_eq!(value["status"], "usage-error");
        assert_eq!(value["stage"], "runtime-input");
        assert!(
            value["primary_diagnostic"]["message"]
                .as_str()
                .unwrap()
                .contains("duplicate")
        );
    }

    #[test]
    fn missing_source_path_is_an_input_failure_with_instance_context() {
        let result = run_cli([
            OPERATION,
            "--instance",
            "missing-instance",
            "--source",
            "/definitely/not/a/body.json",
        ]);
        assert_eq!(result.exit_code, 1);
        let value = value(&result);
        assert_eq!(value["status"], "input-failure");
        assert_eq!(value["instance_id"], "missing-instance");
    }
}
