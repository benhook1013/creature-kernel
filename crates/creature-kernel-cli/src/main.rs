mod provisional_form_inspection;
mod provisional_runtime_input_inspection;
mod source_preparation_inspection;
mod structural_inspection;

fn main() {
    let arguments: Vec<String> = std::env::args().skip(1).collect();
    let (json, exit_code) =
        if arguments.first().map(String::as_str) == Some("inspect-runtime-input") {
            let result = provisional_runtime_input_inspection::run_cli(arguments);
            (result.json, result.exit_code)
        } else if arguments.first().map(String::as_str) == Some("inspect-prepared-source") {
            let result = source_preparation_inspection::run_cli(arguments);
            (result.json, result.exit_code)
        } else if arguments.first().map(String::as_str) == Some("inspect-provisional-form") {
            let result = provisional_form_inspection::run_cli(arguments);
            (result.json, result.exit_code)
        } else {
            let result = structural_inspection::run_cli(arguments);
            (result.json, result.exit_code)
        };
    println!("{json}");
    if exit_code != 0 {
        std::process::exit(exit_code);
    }
}
