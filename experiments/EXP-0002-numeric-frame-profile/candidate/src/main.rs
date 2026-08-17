use std::collections::HashSet;
use std::convert::TryFrom;
use std::fmt;
use std::io::{self, BufRead, BufReader, Write};

#[allow(dead_code)]
mod environment;

use creature_kernel_core::frame::Translation3;
use creature_kernel_core::numeric::{
    DecimalAdmissionError, DecimalResourceLimits, NormalizedBinary64, admit_decimal,
};
use creature_kernel_core::numeric_comparison::{
    InvalidProfileEntry, NumericArithmeticFailure, NumericComparisonError,
    ProvisionalScalarTolerance, ToleranceField,
};
use creature_kernel_core::provisional_json as json;
use serde::de::{self, DeserializeSeed, MapAccess, SeqAccess, Visitor};
use serde::{Deserialize, Deserializer, Serialize};

const REQUEST_PROTOCOL_ID: &str = "ck.r3.numeric-candidate-request-1";
const RESPONSE_PROTOCOL_ID: &str = "ck.r3.numeric-candidate-response-1";
const MAX_FRAME_BYTES: usize = 16_384;
const MAX_REQUEST_ID_BYTES: usize = 256;

enum InputFrame {
    End,
    Record(Vec<u8>),
    Oversized,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct Request {
    protocol_id: String,
    request_id: String,
    operation: String,
    input: json::Value,
}

#[derive(Debug, Serialize)]
struct Response {
    protocol_id: &'static str,
    #[serde(skip_serializing_if = "Option::is_none")]
    request_id: Option<String>,
    status: &'static str,
    #[serde(skip_serializing_if = "Option::is_none")]
    observations: Option<json::Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    error: Option<String>,
}

fn main() -> io::Result<()> {
    let stdin = io::stdin();
    let stdout = io::stdout();
    let mut input = BufReader::new(stdin.lock());
    let mut output = io::BufWriter::new(stdout.lock());

    loop {
        let response = match read_input_frame(&mut input)? {
            InputFrame::End => break,
            InputFrame::Oversized => resource_response(None, "request-line-bytes"),
            InputFrame::Record(bytes) => match std::str::from_utf8(&bytes) {
                Ok(line) if line.trim().is_empty() => error_response(None, "malformed-request"),
                Ok(line) => match parse_request(line) {
                    Ok(request) => dispatch_request(request),
                    Err(_) => error_response(None, "malformed-request"),
                },
                Err(_) => error_response(None, "malformed-request"),
            },
        };
        write_response(&mut output, response)?;
    }

    Ok(())
}

fn read_input_frame(reader: &mut impl BufRead) -> io::Result<InputFrame> {
    let mut frame = Vec::with_capacity(MAX_FRAME_BYTES);
    loop {
        let available = reader.fill_buf()?;
        if available.is_empty() {
            return if frame.is_empty() {
                Ok(InputFrame::End)
            } else {
                Ok(InputFrame::Record(frame))
            };
        }

        let newline = available.iter().position(|byte| *byte == b'\n');
        let take = newline.map_or(available.len(), |index| index + 1);
        if frame.len().saturating_add(take) > MAX_FRAME_BYTES {
            reader.consume(take);
            if newline.is_none() {
                drain_input_record(reader)?;
            }
            return Ok(InputFrame::Oversized);
        }

        frame.extend_from_slice(&available[..take]);
        reader.consume(take);
        if newline.is_some() {
            return Ok(InputFrame::Record(frame));
        }
    }
}

fn drain_input_record(reader: &mut impl BufRead) -> io::Result<()> {
    loop {
        let available = reader.fill_buf()?;
        if available.is_empty() {
            return Ok(());
        }
        let take = available
            .iter()
            .position(|byte| *byte == b'\n')
            .map_or(available.len(), |index| index + 1);
        let has_newline = available[..take].contains(&b'\n');
        reader.consume(take);
        if has_newline {
            return Ok(());
        }
    }
}

fn parse_request(line: &str) -> Result<Request, ()> {
    reject_duplicate_members(line)?;
    json::from_str(line).map_err(|_| ())
}

fn reject_duplicate_members(input: &str) -> Result<(), ()> {
    let mut deserializer = json::Deserializer::from_str(input);
    deserializer
        .deserialize_any(DuplicateKeyVisitor)
        .map_err(|_| ())?;
    deserializer.end().map_err(|_| ())
}

struct DuplicateKeyVisitor;

struct DuplicateValueSeed;

impl<'de> DeserializeSeed<'de> for DuplicateValueSeed {
    type Value = ();

    fn deserialize<D>(self, deserializer: D) -> Result<Self::Value, D::Error>
    where
        D: Deserializer<'de>,
    {
        deserializer.deserialize_any(DuplicateKeyVisitor)
    }
}

impl<'de> Visitor<'de> for DuplicateKeyVisitor {
    type Value = ();

    fn expecting(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("a JSON value without duplicate object members")
    }

    fn visit_bool<E>(self, _value: bool) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        Ok(())
    }

    fn visit_i64<E>(self, _value: i64) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        Ok(())
    }

    fn visit_u64<E>(self, _value: u64) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        Ok(())
    }

    fn visit_f64<E>(self, _value: f64) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        Ok(())
    }

    fn visit_str<E>(self, _value: &str) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        Ok(())
    }

    fn visit_borrowed_str<E>(self, _value: &'de str) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        Ok(())
    }

    fn visit_unit<E>(self) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        Ok(())
    }

    fn visit_seq<A>(self, mut sequence: A) -> Result<Self::Value, A::Error>
    where
        A: SeqAccess<'de>,
    {
        while sequence.next_element_seed(DuplicateValueSeed)?.is_some() {}
        Ok(())
    }

    fn visit_map<A>(self, mut map: A) -> Result<Self::Value, A::Error>
    where
        A: MapAccess<'de>,
    {
        let mut keys = HashSet::new();
        while let Some(key) = map.next_key::<String>()? {
            if !keys.insert(key) {
                return Err(de::Error::custom("duplicate JSON object member"));
            }
            map.next_value_seed(DuplicateValueSeed)?;
        }
        Ok(())
    }
}

fn write_response(output: &mut impl Write, response: Response) -> io::Result<()> {
    let serialized = json::to_string(&response)
        .map_err(|error| io::Error::new(io::ErrorKind::InvalidData, error))?;
    if serialized.len().saturating_add(1) > MAX_FRAME_BYTES {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            "response exceeds frame limit",
        ));
    }
    writeln!(output, "{serialized}")?;
    output.flush()
}

fn handle_request(request: Request) -> Response {
    if request.protocol_id != REQUEST_PROTOCOL_ID || request.request_id.is_empty() {
        return error_response(Some(request.request_id), "malformed-request");
    }

    match request.operation.as_str() {
        "decimal-admission" => decimal_admission(request.request_id, &request.input),
        "scalar-comparison" => scalar_comparison(request.request_id, &request.input),
        "translation-comparison" => translation_comparison(request.request_id, &request.input),
        "environment-attestation" => environment_attestation(request.request_id, &request.input),
        "quaternion-normalization" | "quaternion-comparison" | "quaternion-tuple-predicate" => {
            unsupported(request.request_id, "quaternion-operation-unsupported")
        }
        _ => unsupported(request.request_id, "unsupported-operation"),
    }
}

fn dispatch_request(request: Request) -> Response {
    if request.request_id.len() > MAX_REQUEST_ID_BYTES {
        return error_response(None, "malformed-request");
    }
    handle_request(request)
}

fn environment_attestation(request_id: String, input: &json::Value) -> Response {
    if exact_object(input, &[]).is_err() {
        return error_response(Some(request_id), "invalid-input");
    }

    let observation = environment::observe_environment();
    observed_response(
        request_id,
        json::json!({
            "target": observation.target,
            "status": environment_status_name(observation.status),
            "rounding_mode": observation.rounding_mode,
            "mxcsr": observation.mxcsr.map(|value| format!("0x{value:08x}")),
            "mxcsr_rounding_mode": observation.mxcsr_rounding_mode,
            "ftz_enabled": observation.mxcsr.map(|value| value & (1 << 15) != 0),
            "daz_enabled": observation.mxcsr.map(|value| value & (1 << 6) != 0),
            "failure_classification": failure_classification(observation.failure),
            "scope": "single-threaded-jsonl-loop"
        }),
    )
}

fn environment_status_name(status: environment::EnvironmentStatus) -> &'static str {
    match status {
        environment::EnvironmentStatus::Passed => "passed",
        environment::EnvironmentStatus::Failed => "failed",
        environment::EnvironmentStatus::Unsupported => "unsupported",
    }
}

fn failure_classification(failure: Option<environment::EnvironmentFailure>) -> &'static str {
    match failure {
        None => "none",
        Some(environment::EnvironmentFailure::UnsupportedTarget) => "unsupported-target",
        Some(environment::EnvironmentFailure::RoundingModeUnavailable { .. }) => {
            "rounding-mode-unavailable"
        }
        Some(environment::EnvironmentFailure::WrongRoundingMode { .. }) => "wrong-rounding-mode",
        Some(environment::EnvironmentFailure::FtzEnabled { .. }) => "ftz-enabled",
        Some(environment::EnvironmentFailure::DazEnabled { .. }) => "daz-enabled",
    }
}

fn decimal_admission(request_id: String, input: &json::Value) -> Response {
    let map = match exact_object(
        input,
        &[
            "token",
            "max_token_bytes",
            "max_significant_digits",
            "max_exponent_abs",
        ],
    ) {
        Ok(map) => map,
        Err(()) => return error_response(Some(request_id), "invalid-input"),
    };
    let token = match string_field(map, "token") {
        Ok(value) => value,
        Err(()) => return error_response(Some(request_id), "invalid-input"),
    };
    let max_token_bytes = match usize_field(map, "max_token_bytes") {
        Ok(value) => value,
        Err(()) => return error_response(Some(request_id), "invalid-input"),
    };
    let max_significant_digits = match usize_field(map, "max_significant_digits") {
        Ok(value) => value,
        Err(()) => return error_response(Some(request_id), "invalid-input"),
    };
    let max_exponent_abs = match u32_field(map, "max_exponent_abs") {
        Ok(value) => value,
        Err(()) => return error_response(Some(request_id), "invalid-input"),
    };
    let limits =
        match DecimalResourceLimits::new(max_token_bytes, max_significant_digits, max_exponent_abs)
        {
            Ok(value) => value,
            Err(_) => return error_response(Some(request_id), "invalid-input"),
        };

    match admit_decimal(token, limits) {
        Ok(value) => observed_response(request_id, json::json!({ "bits": bits_string(value) })),
        Err(DecimalAdmissionError::ResourceLimit(limit)) => Response {
            protocol_id: RESPONSE_PROTOCOL_ID,
            request_id: Some(request_id),
            status: "resource-limit",
            observations: None,
            error: Some(limit_name(limit).to_owned()),
        },
        Err(DecimalAdmissionError::Conversion(error)) => Response {
            protocol_id: RESPONSE_PROTOCOL_ID,
            request_id: Some(request_id),
            status: "rejected",
            observations: None,
            error: Some(decimal_conversion_code(error).to_owned()),
        },
    }
}

fn scalar_comparison(request_id: String, input: &json::Value) -> Response {
    let map = match exact_object(
        input,
        &["absolute_bits", "relative_bits", "left_bits", "right_bits"],
    ) {
        Ok(map) => map,
        Err(()) => return error_response(Some(request_id), "invalid-input"),
    };
    let absolute = match bits_field(map, "absolute_bits") {
        Ok(value) => value,
        Err(()) => return error_response(Some(request_id), "invalid-input"),
    };
    let relative = match bits_field(map, "relative_bits") {
        Ok(value) => value,
        Err(()) => return error_response(Some(request_id), "invalid-input"),
    };
    let left = match bits_field(map, "left_bits") {
        Ok(value) => value,
        Err(()) => return error_response(Some(request_id), "invalid-input"),
    };
    let right = match bits_field(map, "right_bits") {
        Ok(value) => value,
        Err(()) => return error_response(Some(request_id), "invalid-input"),
    };
    let tolerance = match ProvisionalScalarTolerance::new(absolute, relative) {
        Ok(value) => value,
        Err(error) => return numeric_comparison_response(request_id, error),
    };
    match tolerance.compare_scalar(left, right) {
        Ok(predicate) => predicate_response(request_id, predicate),
        Err(error) => numeric_comparison_response(request_id, error),
    }
}

fn translation_comparison(request_id: String, input: &json::Value) -> Response {
    let map = match exact_object(
        input,
        &["absolute_bits", "relative_bits", "left_bits", "right_bits"],
    ) {
        Ok(map) => map,
        Err(()) => return error_response(Some(request_id), "invalid-input"),
    };
    let absolute = match bits_field(map, "absolute_bits") {
        Ok(value) => value,
        Err(()) => return error_response(Some(request_id), "invalid-input"),
    };
    let relative = match bits_field(map, "relative_bits") {
        Ok(value) => value,
        Err(()) => return error_response(Some(request_id), "invalid-input"),
    };
    let left = match translation_field(map, "left_bits") {
        Ok(value) => value,
        Err(()) => return error_response(Some(request_id), "invalid-input"),
    };
    let right = match translation_field(map, "right_bits") {
        Ok(value) => value,
        Err(()) => return error_response(Some(request_id), "invalid-input"),
    };
    let tolerance = match ProvisionalScalarTolerance::new(absolute, relative) {
        Ok(value) => value,
        Err(error) => return numeric_comparison_response(request_id, error),
    };
    match tolerance.compare_translation(left, right) {
        Ok(predicate) => predicate_response(request_id, predicate),
        Err(error) => numeric_comparison_response(request_id, error),
    }
}

fn decimal_conversion_code(
    error: creature_kernel_core::numeric::DecimalConversionError,
) -> &'static str {
    match error {
        creature_kernel_core::numeric::DecimalConversionError::InvalidJsonNumber => {
            "invalid-json-number"
        }
        creature_kernel_core::numeric::DecimalConversionError::NonFiniteOrOverflow => {
            "non-finite-or-overflow"
        }
        creature_kernel_core::numeric::DecimalConversionError::NonzeroUnderflowToZero => {
            "nonzero-underflow-to-zero"
        }
    }
}

fn numeric_comparison_response(request_id: String, error: NumericComparisonError) -> Response {
    match error {
        NumericComparisonError::InvalidProfileEntry(entry) => {
            let code = match entry {
                InvalidProfileEntry::NonFinite { field } => nonfinite_tolerance_code(field),
                InvalidProfileEntry::Negative { field } => negative_tolerance_code(field),
            };
            Response {
                protocol_id: RESPONSE_PROTOCOL_ID,
                request_id: Some(request_id),
                status: "rejected",
                observations: None,
                error: Some(code.to_owned()),
            }
        }
        NumericComparisonError::ExactArithmetic(failure) => Response {
            protocol_id: RESPONSE_PROTOCOL_ID,
            request_id: Some(request_id),
            status: "error",
            observations: None,
            error: Some(exact_arithmetic_code(failure).to_owned()),
        },
    }
}

fn negative_tolerance_code(field: ToleranceField) -> &'static str {
    match field {
        ToleranceField::Absolute => "negative-absolute-tolerance",
        ToleranceField::Relative => "negative-relative-tolerance",
        ToleranceField::QuaternionHalfChord => "negative-quaternion-half-chord-tolerance",
    }
}

fn nonfinite_tolerance_code(field: ToleranceField) -> &'static str {
    match field {
        ToleranceField::Absolute => "non-finite-absolute-tolerance",
        ToleranceField::Relative => "non-finite-relative-tolerance",
        ToleranceField::QuaternionHalfChord => "non-finite-quaternion-half-chord-tolerance",
    }
}

fn exact_arithmetic_code(failure: NumericArithmeticFailure) -> &'static str {
    match failure {
        NumericArithmeticFailure::NonFinite => "exact-arithmetic-non-finite",
        NumericArithmeticFailure::TemporaryLimitExceeded => "exact-arithmetic-temporary-limit",
        NumericArithmeticFailure::ExponentOverflow => "exact-arithmetic-exponent-overflow",
        NumericArithmeticFailure::ShiftOverflow => "exact-arithmetic-shift-overflow",
    }
}

fn exact_object<'a>(
    value: &'a json::Value,
    expected: &[&str],
) -> Result<&'a json::Map<String, json::Value>, ()> {
    let map = value.as_object().ok_or(())?;
    if map.len() == expected.len() && expected.iter().all(|key| map.contains_key(*key)) {
        Ok(map)
    } else {
        Err(())
    }
}

fn string_field<'a>(map: &'a json::Map<String, json::Value>, name: &str) -> Result<&'a str, ()> {
    map.get(name).and_then(json::Value::as_str).ok_or(())
}

fn usize_field(map: &json::Map<String, json::Value>, name: &str) -> Result<usize, ()> {
    let value = string_field(map, name)?;
    parse_unsigned(value).and_then(|value| usize::try_from(value).map_err(|_| ()))
}

fn u32_field(map: &json::Map<String, json::Value>, name: &str) -> Result<u32, ()> {
    let value = string_field(map, name)?;
    parse_unsigned(value).and_then(|value| u32::try_from(value).map_err(|_| ()))
}

fn parse_unsigned(value: &str) -> Result<u64, ()> {
    if value.is_empty() || !value.bytes().all(|byte| byte.is_ascii_digit()) {
        return Err(());
    }
    value.parse().map_err(|_| ())
}

fn bits_field(map: &json::Map<String, json::Value>, name: &str) -> Result<NormalizedBinary64, ()> {
    let value = string_field(map, name)?;
    parse_bits(value)
}

fn parse_bits(value: &str) -> Result<NormalizedBinary64, ()> {
    if value.len() != 18
        || !value.starts_with("0x")
        || !value.as_bytes()[2..].iter().all(u8::is_ascii_hexdigit)
    {
        return Err(());
    }
    let bits = u64::from_str_radix(&value[2..], 16).map_err(|_| ())?;
    NormalizedBinary64::from_bits(bits).map_err(|_| ())
}

fn translation_field(map: &json::Map<String, json::Value>, name: &str) -> Result<Translation3, ()> {
    let values = map.get(name).and_then(json::Value::as_array).ok_or(())?;
    if values.len() != 3 {
        return Err(());
    }
    let mut components = [NormalizedBinary64::ZERO; 3];
    for (index, value) in values.iter().enumerate() {
        let bits = value.as_str().ok_or(())?;
        components[index] = parse_bits(bits)?;
    }
    Ok(Translation3::from_components(components))
}

fn bits_string(value: NormalizedBinary64) -> String {
    format!("0x{:016x}", value.to_bits())
}

fn limit_name(limit: creature_kernel_core::numeric::DecimalResourceLimit) -> &'static str {
    match limit {
        creature_kernel_core::numeric::DecimalResourceLimit::TokenBytes => "token-bytes",
        creature_kernel_core::numeric::DecimalResourceLimit::SignificantDigits => {
            "significant-digits"
        }
        creature_kernel_core::numeric::DecimalResourceLimit::ExponentMagnitude => {
            "exponent-magnitude"
        }
    }
}

fn observed_response(request_id: String, observations: json::Value) -> Response {
    Response {
        protocol_id: RESPONSE_PROTOCOL_ID,
        request_id: Some(request_id),
        status: "observed",
        observations: Some(observations),
        error: None,
    }
}

fn predicate_response(request_id: String, predicate: bool) -> Response {
    Response {
        protocol_id: RESPONSE_PROTOCOL_ID,
        request_id: Some(request_id),
        status: "observed",
        observations: Some(json::json!({ "predicate": predicate })),
        error: None,
    }
}

fn unsupported(request_id: String, error: &str) -> Response {
    Response {
        protocol_id: RESPONSE_PROTOCOL_ID,
        request_id: Some(request_id),
        status: "unsupported",
        observations: None,
        error: Some(error.to_owned()),
    }
}

fn error_response(request_id: Option<String>, error: impl Into<String>) -> Response {
    Response {
        protocol_id: RESPONSE_PROTOCOL_ID,
        request_id,
        status: "error",
        observations: None,
        error: Some(error.into()),
    }
}

fn resource_response(request_id: Option<String>, error: &str) -> Response {
    Response {
        protocol_id: RESPONSE_PROTOCOL_ID,
        request_id,
        status: "resource-limit",
        observations: None,
        error: Some(error.to_owned()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn request(operation: &str, input: json::Value) -> Request {
        Request {
            protocol_id: REQUEST_PROTOCOL_ID.to_owned(),
            request_id: "opaque-1".to_owned(),
            operation: operation.to_owned(),
            input,
        }
    }

    fn valid_decimal_line() -> Vec<u8> {
        br#"{"protocol_id":"ck.r3.numeric-candidate-request-1","request_id":"after-frame","operation":"decimal-admission","input":{"token":"0.1","max_token_bytes":"512","max_significant_digits":"128","max_exponent_abs":"10000"}}"#
            .to_vec()
    }

    #[test]
    fn oversized_frame_emits_resource_code_and_recovers() {
        let mut bytes = vec![b'x'; MAX_FRAME_BYTES + 1];
        bytes.push(b'\n');
        bytes.extend_from_slice(&valid_decimal_line());
        bytes.push(b'\n');
        let mut reader = BufReader::new(bytes.as_slice());

        assert!(matches!(
            read_input_frame(&mut reader).unwrap(),
            InputFrame::Oversized
        ));
        let InputFrame::Record(record) = read_input_frame(&mut reader).unwrap() else {
            panic!("valid record was not recovered after oversized frame");
        };
        let response =
            handle_request(parse_request(std::str::from_utf8(&record).unwrap()).unwrap());
        assert_eq!(response.status, "observed");
        let response = resource_response(None, "request-line-bytes");
        assert_eq!(response.status, "resource-limit");
        assert_eq!(response.error.as_deref(), Some("request-line-bytes"));
    }

    #[test]
    fn invalid_utf8_frame_is_malformed_and_recovers() {
        let mut bytes = vec![0xff, b'\n'];
        bytes.extend_from_slice(&valid_decimal_line());
        bytes.push(b'\n');
        let mut reader = BufReader::new(bytes.as_slice());

        let InputFrame::Record(record) = read_input_frame(&mut reader).unwrap() else {
            panic!("invalid UTF-8 record was not read");
        };
        let response = match std::str::from_utf8(&record) {
            Ok(_) => panic!("invalid UTF-8 unexpectedly decoded"),
            Err(_) => error_response(None, "malformed-request"),
        };
        assert_eq!(response.status, "error");
        let InputFrame::Record(record) = read_input_frame(&mut reader).unwrap() else {
            panic!("valid record was not recovered after invalid UTF-8");
        };
        assert_eq!(
            handle_request(parse_request(std::str::from_utf8(&record).unwrap()).unwrap()).status,
            "observed"
        );
    }

    #[test]
    fn write_failure_propagates() {
        struct FailingWriter;

        impl Write for FailingWriter {
            fn write(&mut self, _bytes: &[u8]) -> io::Result<usize> {
                Err(io::Error::new(
                    io::ErrorKind::BrokenPipe,
                    "synthetic write failure",
                ))
            }

            fn flush(&mut self) -> io::Result<()> {
                Err(io::Error::new(
                    io::ErrorKind::BrokenPipe,
                    "synthetic flush failure",
                ))
            }
        }

        let result = write_response(
            &mut FailingWriter,
            error_response(None, "malformed-request"),
        );
        assert_eq!(result.unwrap_err().kind(), io::ErrorKind::BrokenPipe);
    }

    #[test]
    fn successful_write_then_flush_failure_propagates() {
        struct FlushFailure {
            bytes: Vec<u8>,
        }

        impl Write for FlushFailure {
            fn write(&mut self, bytes: &[u8]) -> io::Result<usize> {
                self.bytes.extend_from_slice(bytes);
                Ok(bytes.len())
            }

            fn flush(&mut self) -> io::Result<()> {
                Err(io::Error::new(
                    io::ErrorKind::BrokenPipe,
                    "synthetic flush failure",
                ))
            }
        }

        let mut writer = FlushFailure { bytes: Vec::new() };
        let result = write_response(&mut writer, error_response(None, "malformed-request"));
        assert!(!writer.bytes.is_empty());
        assert_eq!(result.unwrap_err().kind(), io::ErrorKind::BrokenPipe);
    }

    #[test]
    fn exact_cap_lf_is_a_single_record() {
        let mut bytes = valid_decimal_line();
        bytes.resize(MAX_FRAME_BYTES - 1, b' ');
        bytes.push(b'\n');
        let mut reader = BufReader::new(bytes.as_slice());

        let InputFrame::Record(record) = read_input_frame(&mut reader).unwrap() else {
            panic!("exact-cap LF record was not read");
        };
        assert_eq!(record.len(), MAX_FRAME_BYTES);
        assert!(matches!(
            read_input_frame(&mut reader).unwrap(),
            InputFrame::End
        ));
    }

    #[test]
    fn exact_cap_eof_is_a_single_record() {
        let mut bytes = valid_decimal_line();
        bytes.resize(MAX_FRAME_BYTES, b' ');
        let mut reader = BufReader::new(bytes.as_slice());

        let InputFrame::Record(record) = read_input_frame(&mut reader).unwrap() else {
            panic!("exact-cap EOF record was not read");
        };
        assert_eq!(record.len(), MAX_FRAME_BYTES);
        assert!(matches!(
            read_input_frame(&mut reader).unwrap(),
            InputFrame::End
        ));
    }

    #[test]
    fn cap_plus_one_eof_is_oversized_and_recovers_to_eof() {
        let bytes = vec![b'x'; MAX_FRAME_BYTES + 1];
        let mut reader = BufReader::new(bytes.as_slice());

        assert!(matches!(
            read_input_frame(&mut reader).unwrap(),
            InputFrame::Oversized
        ));
        assert!(matches!(
            read_input_frame(&mut reader).unwrap(),
            InputFrame::End
        ));
    }

    #[test]
    fn cr_and_crlf_bytes_count_toward_frame_cap() {
        let mut crlf = vec![b'x'; MAX_FRAME_BYTES - 2];
        crlf.extend_from_slice(b"\r\n");
        let mut reader = BufReader::new(crlf.as_slice());
        let InputFrame::Record(record) = read_input_frame(&mut reader).unwrap() else {
            panic!("exact-cap CRLF record was not read");
        };
        assert_eq!(record.len(), MAX_FRAME_BYTES);

        let mut oversized_crlf = vec![b'x'; MAX_FRAME_BYTES - 1];
        oversized_crlf.extend_from_slice(b"\r\n");
        let mut reader = BufReader::new(oversized_crlf.as_slice());
        assert!(matches!(
            read_input_frame(&mut reader).unwrap(),
            InputFrame::Oversized
        ));

        let mut cr_eof = vec![b'x'; MAX_FRAME_BYTES - 1];
        cr_eof.push(b'\r');
        let mut reader = BufReader::new(cr_eof.as_slice());
        let InputFrame::Record(record) = read_input_frame(&mut reader).unwrap() else {
            panic!("exact-cap CR EOF record was not read");
        };
        assert_eq!(record.len(), MAX_FRAME_BYTES);
    }

    #[test]
    fn oversized_request_id_is_not_echoed_and_max_id_environment_fits_cap() {
        let oversized_id = format!("{}a", "é".repeat(MAX_REQUEST_ID_BYTES / 2));
        assert_eq!(oversized_id.len(), MAX_REQUEST_ID_BYTES + 1);
        let oversized = dispatch_request(Request {
            protocol_id: REQUEST_PROTOCOL_ID.to_owned(),
            request_id: oversized_id,
            operation: "decimal-admission".to_owned(),
            input: json::json!({}),
        });
        assert_eq!(oversized.status, "error");
        assert_eq!(oversized.error.as_deref(), Some("malformed-request"));
        assert!(oversized.request_id.is_none());
        let serialized = json::to_string(&oversized).unwrap();
        assert!(serialized.len() < MAX_FRAME_BYTES);

        let maximum_id = "\0".repeat(MAX_REQUEST_ID_BYTES);
        assert_eq!(maximum_id.len(), MAX_REQUEST_ID_BYTES);
        let environment = dispatch_request(Request {
            protocol_id: REQUEST_PROTOCOL_ID.to_owned(),
            request_id: maximum_id,
            operation: "environment-attestation".to_owned(),
            input: json::json!({}),
        });
        let serialized = json::to_string(&environment).unwrap();
        assert!(serialized.len() < MAX_FRAME_BYTES);
    }

    #[test]
    fn wire_error_codes_are_stable_and_statuses_are_consistent() {
        use creature_kernel_core::numeric::DecimalConversionError;

        assert_eq!(
            decimal_conversion_code(DecimalConversionError::InvalidJsonNumber),
            "invalid-json-number"
        );
        assert_eq!(
            decimal_conversion_code(DecimalConversionError::NonFiniteOrOverflow),
            "non-finite-or-overflow"
        );
        assert_eq!(
            decimal_conversion_code(DecimalConversionError::NonzeroUnderflowToZero),
            "nonzero-underflow-to-zero"
        );

        let negative = numeric_comparison_response(
            "opaque".to_owned(),
            NumericComparisonError::InvalidProfileEntry(InvalidProfileEntry::Negative {
                field: ToleranceField::Absolute,
            }),
        );
        assert_eq!(negative.status, "rejected");
        assert_eq!(
            negative.error.as_deref(),
            Some("negative-absolute-tolerance")
        );

        let arithmetic = numeric_comparison_response(
            "opaque".to_owned(),
            NumericComparisonError::ExactArithmetic(
                NumericArithmeticFailure::TemporaryLimitExceeded,
            ),
        );
        assert_eq!(arithmetic.status, "error");
        assert_eq!(
            arithmetic.error.as_deref(),
            Some("exact-arithmetic-temporary-limit")
        );
    }

    #[test]
    fn decimal_and_negative_tolerance_requests_use_stable_codes() {
        let rejected = handle_request(request(
            "decimal-admission",
            json::json!({
                "token": "1e309",
                "max_token_bytes": "512",
                "max_significant_digits": "128",
                "max_exponent_abs": "10000"
            }),
        ));
        assert_eq!(rejected.status, "rejected");
        assert_eq!(rejected.error.as_deref(), Some("non-finite-or-overflow"));

        let negative = handle_request(request(
            "scalar-comparison",
            json::json!({
                "absolute_bits": "0xbff0000000000000",
                "relative_bits": "0x0000000000000000",
                "left_bits": "0x0000000000000000",
                "right_bits": "0x0000000000000000"
            }),
        ));
        assert_eq!(negative.status, "rejected");
        assert_eq!(
            negative.error.as_deref(),
            Some("negative-absolute-tolerance")
        );
    }

    #[test]
    fn decimal_admission_returns_canonical_bits() {
        let response = handle_request(request(
            "decimal-admission",
            json::json!({
                "token": "0.1",
                "max_token_bytes": "512",
                "max_significant_digits": "128",
                "max_exponent_abs": "10000"
            }),
        ));
        assert_eq!(response.status, "observed");
        assert_eq!(response.protocol_id, RESPONSE_PROTOCOL_ID);
        let serialized = json::to_string(&response).unwrap();
        assert!(serialized.contains("\"protocol_id\":\"ck.r3.numeric-candidate-response-1\""));
        assert_eq!(response.observations.unwrap()["bits"], "0x3fb999999999999a");
    }

    #[test]
    fn scalar_comparison_returns_false_as_an_observation() {
        let response = handle_request(request(
            "scalar-comparison",
            json::json!({
                "absolute_bits": "0x0000000000000000",
                "relative_bits": "0x0000000000000000",
                "left_bits": "0x3ff0000000000000",
                "right_bits": "0x3ff0000000000001"
            }),
        ));
        assert_eq!(response.status, "observed");
        assert_eq!(response.observations.unwrap()["predicate"], false);
    }

    #[test]
    fn translation_comparison_accepts_componentwise_equal_values() {
        let response = handle_request(request(
            "translation-comparison",
            json::json!({
                "absolute_bits": "0x0000000000000000",
                "relative_bits": "0x0000000000000000",
                "left_bits": ["0x0000000000000000", "0x8000000000000000", "0x0000000000000001"],
                "right_bits": ["0x0000000000000000", "0x0000000000000000", "0x0000000000000001"]
            }),
        ));
        assert_eq!(response.status, "observed");
        assert_eq!(response.observations.unwrap()["predicate"], true);
    }

    #[test]
    fn quaternion_operations_are_explicitly_unsupported() {
        let response = handle_request(request("quaternion-normalization", json::json!({})));
        assert_eq!(response.status, "unsupported");
        assert_eq!(
            response.error.as_deref(),
            Some("quaternion-operation-unsupported")
        );
    }

    #[test]
    fn environment_attestation_emits_same_process_evidence_without_sqrt() {
        let response = handle_request(request("environment-attestation", json::json!({})));
        assert_eq!(response.status, "observed");
        let observations = response.observations.unwrap();
        assert!(observations["target"].as_str().is_some());
        assert!(matches!(
            observations["status"].as_str(),
            Some("passed" | "failed" | "unsupported")
        ));
        assert!(observations["failure_classification"].as_str().is_some());
        assert_eq!(observations["scope"], "single-threaded-jsonl-loop");
        assert!(
            observations["mxcsr_rounding_mode"].is_null()
                || observations["mxcsr_rounding_mode"]
                    .as_u64()
                    .is_some_and(|mode| mode <= 3)
        );
        assert!(observations.get("subnormal_add_bits").is_none());
        assert!(observations.get("subnormal_multiply_bits").is_none());
        if let Some(mxcsr) = observations["mxcsr"].as_str() {
            assert_eq!(mxcsr.len(), 10);
            assert!(mxcsr.starts_with("0x"));
        }
    }

    #[test]
    fn request_protocol_mismatch_is_malformed() {
        let mut request = request("decimal-admission", json::json!({}));
        request.protocol_id = "wrong-protocol".to_owned();
        let response = handle_request(request);
        assert_eq!(response.status, "error");
        assert_eq!(response.error.as_deref(), Some("malformed-request"));
        assert_eq!(response.protocol_id, RESPONSE_PROTOCOL_ID);
    }

    fn assert_duplicate_rejected_then_valid_request_parses(line: &str) {
        assert!(parse_request(line).is_err());
        let valid = r#"{"protocol_id":"ck.r3.numeric-candidate-request-1","request_id":"opaque-valid","operation":"decimal-admission","input":{"token":"0.1","max_token_bytes":"512","max_significant_digits":"128","max_exponent_abs":"10000"}}"#;
        let response = handle_request(parse_request(valid).expect("valid follow-up request"));
        assert_eq!(response.status, "observed");
    }

    #[test]
    fn duplicate_top_level_member_is_malformed() {
        assert_duplicate_rejected_then_valid_request_parses(
            r#"{"protocol_id":"ck.r3.numeric-candidate-request-1","request_id":"opaque-1","operation":"decimal-admission","operation":"decimal-admission","input":{}}"#,
        );
    }

    #[test]
    fn duplicate_nested_scalar_tolerance_member_is_malformed() {
        assert_duplicate_rejected_then_valid_request_parses(
            r#"{"protocol_id":"ck.r3.numeric-candidate-request-1","request_id":"opaque-1","operation":"scalar-comparison","input":{"absolute_bits":"0x0000000000000000","absolute_bits":"0x0000000000000000","relative_bits":"0x0000000000000000","left_bits":"0x3ff0000000000000","right_bits":"0x3ff0000000000001"}}"#,
        );
    }

    #[test]
    fn duplicate_nested_decimal_member_is_malformed() {
        assert_duplicate_rejected_then_valid_request_parses(
            r#"{"protocol_id":"ck.r3.numeric-candidate-request-1","request_id":"opaque-1","operation":"decimal-admission","input":{"token":"0.1","max_token_bytes":"512","max_token_bytes":"512","max_significant_digits":"128","max_exponent_abs":"10000"}}"#,
        );
    }

    #[test]
    fn malformed_request_does_not_leak_expected_fields() {
        let line = r#"{"protocol_id":"ck.r3.numeric-candidate-request-1","request_id":"opaque-1","operation":"decimal-admission","input":{},"expected":"secret"}"#;
        let response = parse_request(line)
            .map(handle_request)
            .unwrap_or_else(|_| error_response(None, "malformed-request"));
        let serialized = json::to_string(&response).unwrap();
        assert_eq!(response.status, "error");
        assert!(!serialized.contains("expected"));
        assert!(!serialized.contains("secret"));
    }
}
