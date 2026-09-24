import streamlit as st

from modules.pipeline import run_pipeline_as_dict

st.set_page_config(
    page_title="SecureCode AI - MyWebride",
    page_icon="🔐",
    layout="wide",
)

st.title("🔐 SecureCode AI")
st.caption(
    "Multimodal LLM-Driven Secure Code Synthesis, Debugging, Testing, and Analysis Framework"
)

st.sidebar.header("Input Mode")
mode = st.sidebar.radio(
    "Choose input type",
    ["Text Prompt", "Paste Code", "Image Upload"],
    index=0,
)

st.sidebar.markdown("---")
st.sidebar.markdown("### Pipeline")
st.sidebar.write("1. Route input")
st.sidebar.write("2. Generate or analyze code")
st.sidebar.write("3. Check dependencies")
st.sidebar.write("4. Run static analysis")
st.sidebar.write("5. Run sandbox execution")
st.sidebar.write("6. Generate and run tests")
st.sidebar.write("7. Build unified report")

text_prompt = ""
code_input = ""
image_input = None

if mode == "Text Prompt":
    st.subheader("Text Prompt Input")
    text_prompt = st.text_area(
        "Describe what you want to build:",
        height=140,
        placeholder="Example: Create a password hashing function using bcrypt",
    )

elif mode == "Paste Code":
    st.subheader("Paste Code Input")
    code_input = st.text_area(
        "Paste your Python code here:",
        height=220,
        placeholder="Paste code to analyze, debug, or test...",
    )

elif mode == "Image Upload":
    st.subheader("Image Upload Input")
    image_input = st.file_uploader(
        "Upload a screenshot of code",
        type=["png", "jpg", "jpeg", "webp", "bmp", "tiff"],
    )

st.markdown("---")

run_button = st.button("🚀 Run SecureCode Pipeline", type="primary")


def _render_code_block(title: str, value: str, language: str = "python") -> None:
    st.subheader(title)
    if value and value.strip():
        st.code(value, language=language)
    else:
        st.info("No content available.")


def _render_metrics(summary: dict) -> None:
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Static Issues", summary.get("total_static_issues", 0))
    col2.metric("Bandit Issues", summary.get("bandit_issues", 0))
    col3.metric("Semgrep Findings", summary.get("semgrep_findings", 0))

    pylint_score = summary.get("pylint_score", None)
    col4.metric(
        "Pylint Score",
        "N/A" if pylint_score is None else f"{pylint_score}/10",
    )

    col5, col6, col7 = st.columns(3)
    col5.metric("Pytest Passed", summary.get("pytest_passed", 0))
    col6.metric("Pytest Failed", summary.get("pytest_failed", 0))
    col7.metric("Pytest Skipped", summary.get("pytest_skipped", 0))

    dep_col1, dep_col2 = st.columns(2)
    dep_col1.metric("Missing Dependencies", summary.get("dependency_missing_count", 0))


if run_button:
    if mode == "Text Prompt" and not text_prompt.strip():
        st.warning("Please enter a prompt.")
        st.stop()

    if mode == "Paste Code" and not code_input.strip():
        st.warning("Please paste some code.")
        st.stop()

    if mode == "Image Upload" and image_input is None:
        st.warning("Please upload an image.")
        st.stop()

    with st.spinner("Running pipeline..."):
        report = run_pipeline_as_dict(
            text_prompt=text_prompt,
            code_input=code_input,
            image_input=image_input,
        )

    st.session_state["last_report"] = report
    st.success("Pipeline completed.")

report = st.session_state.get("last_report")

input_mode = report.get("meta", {}).get("input_mode", "") if report else ""
is_prompt_mode = input_mode == "text_prompt"
is_code_mode = input_mode == "code_input"

if report:
    meta = report.get("meta", {})
    code_data = report.get("code", {})
    llm_data = report.get("llm", {})
    analysis_data = report.get("analysis", {})
    pytest_data = report.get("pytest", {})
    summary = analysis_data.get("summary", {})
    dependencies = analysis_data.get("dependencies", {})
    bug_explanation = llm_data.get("bug_explanation", "")

    st.markdown("## Result Overview")

    col1, col2 = st.columns(2)
    with col1:
        st.info(f"Input Mode: **{meta.get('input_mode', 'N/A')}**")
    with col2:
        st.info(f"Status: **{meta.get('status', 'N/A')}**")

    notes = meta.get("notes", [])
    if notes:
        with st.expander("Notes / Pipeline Messages", expanded=False):
            for note in notes:
                st.write(f"- {note}")

    st.markdown("## Analysis Summary")
    _render_metrics(summary)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["Generated / Input Code", "Static Analysis", "Dependencies", "Pytest Results", "Bug Explanation"]
    )

    with tab1:
        original_input = code_data.get("original_input", "")
        generated_code = code_data.get("generated_code", "")
        fixed_code = code_data.get("fixed_code", "")
        generated_tests = code_data.get("generated_tests", "")

        if original_input:
            if is_prompt_mode:
                st.subheader("Original Prompt")
            elif is_code_mode:
                st.subheader("Original Code")
            else:
                st.subheader("Original Input")
            st.code(original_input, language="python")

        if generated_code:
            if is_prompt_mode:
                st.subheader("Generated Code")
            elif is_code_mode:
                st.subheader("Original Code")
            else:
                st.subheader("Generated / Routed Code")
            st.code(generated_code, language="python")

        if fixed_code:
            st.subheader("Fixed Code")
            st.code(fixed_code, language="python")

        if generated_tests:
            st.subheader("Generated Pytest Suite")
            st.code(generated_tests, language="python")

    with tab2:
        st.subheader("Bandit")
        st.text(analysis_data.get("bandit", "No Bandit output."))

        st.subheader("Pylint")
        st.text(analysis_data.get("pylint", "No Pylint output."))

        st.subheader("Semgrep")
        st.text(analysis_data.get("semgrep", "No Semgrep output."))

    with tab3:
        st.subheader("Dependency Report")
        st.json(dependencies)

        missing_modules = analysis_data.get("missing_modules", [])
        install_command = analysis_data.get("install_command", "")

        if missing_modules:
            st.error(f"Missing modules detected: {', '.join(missing_modules)}")
            if install_command:
                st.code(install_command, language="bash")
        else:
            st.success("No missing third-party dependencies detected.")

    with tab4:
        st.subheader("Pytest Output")
        st.text(pytest_data.get("output", "No pytest output."))

        if pytest_data.get("errors"):
            st.subheader("Pytest Errors")
            st.code(pytest_data.get("errors", ""), language="text")

        st.subheader("Pytest Details")
        st.json(pytest_data.get("details", {}))

    with tab5:
        if bug_explanation:
            st.markdown(bug_explanation)
        else:
            st.info("No bug explanation available for this run.")

    with st.expander("Raw Unified Report JSON", expanded=False):
        st.json(report)