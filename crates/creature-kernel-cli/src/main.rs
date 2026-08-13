mod structural_inspection;

fn main() {
    let result = structural_inspection::run_cli(std::env::args().skip(1));
    println!("{}", result.json);
    if result.exit_code != 0 {
        std::process::exit(result.exit_code);
    }
}
