# 🔐 SecureCode AI

### Multimodal LLM-Driven Secure Code Synthesis, Debugging, Testing & Static Analysis Framework

SecureCode AI is a **Python-based developer security and code-analysis framework** that combines **Large Language Models (LLMs)** with traditional static-analysis and testing tools to assist with code generation, security analysis, debugging, automated remediation, dependency inspection, execution, and test generation.

The application provides a **Streamlit-based interface** through which users can submit a natural-language programming request, paste source code, or upload a screenshot of code. Uploaded screenshots are processed through OCR before entering the analysis pipeline.

The framework follows a security-oriented workflow:

> **Input → Code Generation / Extraction → Dependency Analysis → Static Security Analysis → Automated Remediation → Controlled Execution → Test Generation → Pytest Validation → Unified Report**

---

## ✨ Key Features

### 🧠 Multimodal Code Input

SecureCode AI accepts code-related input through three modes:

* **Text Prompt** — describe the functionality you want to build.
* **Paste Code** — submit existing Python code for analysis, debugging, and testing.
* **Image Upload** — upload a screenshot of source code and extract candidate code using OCR.

This allows the framework to operate across both conventional text-based development workflows and image-based code input.

---

### 🤖 LLM-Assisted Code Synthesis

Natural-language programming requests can be converted into Python code using a Groq-hosted LLM.

Example:

```text
Create a password hashing function using bcrypt.
```

The framework routes the request through the LLM layer and passes the resulting code through the downstream analysis pipeline.

The LLM integration is abstracted behind a reusable interface in:

```text
modules/llm_core.py
```

The current default model configuration is:

```text
openai/gpt-oss-120b
```

The model can also be configured through the environment:

```env
GROQ_MODEL=openai/gpt-oss-120b
```

---

### 🖼️ Screenshot-to-Code OCR

The Image Upload workflow uses:

* Pillow
* pytesseract
* Tesseract OCR

Supported image formats include:

```text
PNG
JPG
JPEG
WEBP
BMP
TIFF
```

The OCR pipeline performs basic preprocessing before extraction:

1. Image loading
2. Grayscale conversion
3. Autocontrast
4. Sharpening
5. Contrast enhancement
6. Tesseract OCR
7. Text cleanup
8. Code-likeness detection

The extracted text is then routed into the normal code-analysis pipeline.

> **Note:** OCR output is treated as candidate source code. Formatting and indentation may require correction, especially for indentation-sensitive languages such as Python.

---

### 🛡️ Static Security Analysis

SecureCode AI integrates multiple static-analysis tools:

#### Bandit

Used for identifying common Python security issues and generating security-oriented feedback for automated remediation.

#### Pylint

Used for code-quality analysis and style feedback.

The framework can use Pylint findings as input to an LLM-assisted code-quality remediation pass.

#### Semgrep

Used as an additional pattern-based static-analysis layer for source-code findings.

Using multiple analyzers provides different perspectives on the submitted code rather than relying exclusively on an LLM.

---

### 🔧 LLM-Assisted Security & Quality Remediation

The framework can use findings from static analysis as feedback for an LLM-assisted remediation step.

The pipeline contains separate remediation paths for:

* Security findings
* Code-quality findings

For security findings, the framework constructs security-focused remediation instructions and explicitly instructs the LLM to avoid introducing hardcoded credentials or reproducing the detected vulnerability.

After remediation, static analysis is run again to provide another validation signal.

Conceptually:

```text
Source Code
    ↓
Bandit / Pylint / Semgrep
    ↓
Findings
    ↓
LLM-assisted remediation
    ↓
Re-analysis
```

This creates a feedback loop instead of treating the first generated code version as final.

---

### 📦 Dependency Analysis

SecureCode AI performs source-level dependency inspection using Python AST-based analysis.

The dependency layer identifies:

* Imported modules
* Standard-library modules
* Third-party modules
* Potentially missing dependencies
* Suggested installation commands

The pipeline can therefore identify dependency-related problems before attempting downstream execution and testing.

---

### ⚙️ Controlled Code Execution

The framework includes subprocess-based execution with configurable timeouts.

Current pipeline defaults include:

```text
Code execution timeout : 10 seconds
Pytest timeout         : 30 seconds
```

Execution results can be used to detect runtime failures.

When execution fails, the framework can invoke the debugging/remediation workflow.

> **Security note:** This is controlled subprocess-based execution, not a hardened OS-level or container-isolated sandbox. Untrusted code should not be treated as completely isolated merely because a timeout is applied.

---

### 🐛 LLM-Assisted Debugging

When dynamic execution produces an error, SecureCode AI can pass the execution output to the LLM debugging layer.

The workflow is:

```text
Execute Code
     ↓
Runtime Failure
     ↓
Capture Error
     ↓
LLM Bug Explanation
     ↓
LLM-Assisted Fix
```

The application exposes the resulting explanation and fixed code through the Streamlit interface.

---

### 🧪 Automated Test Generation

The framework uses the LLM to generate a Pytest suite for the analyzed code.

Generated tests are then executed using:

```text
pytest
```

The application reports:

* Number of generated tests
* Passed tests
* Failed tests
* Skipped tests
* Pytest output
* Test errors

This creates an additional validation stage after code analysis and remediation.

> Generated tests are treated as an additional validation signal and are not assumed to be mathematically complete or guaranteed to cover every behavior.

---

### 📊 Unified Analysis Report

Results from different pipeline stages are consolidated into a structured report.

The report can contain:

```text
Input metadata
Code
Generated code
Fixed code
Generated tests
LLM information
Bandit results
Pylint results
Semgrep results
Dependency information
Execution information
Pytest results
Bug explanation
Pipeline notes
```

The Streamlit application presents the results through dedicated sections and also exposes the raw unified report as JSON.

---

# 🏗️ System Architecture

```text
                         ┌─────────────────────┐
                         │    Streamlit UI     │
                         └──────────┬──────────┘
                                    │
                  ┌─────────────────┼─────────────────┐
                  │                 │                 │
                  ▼                 ▼                 ▼
           Text Prompt         Paste Code       Image Upload
                  │                 │                 │
                  │                 │                 ▼
                  │                 │          Pillow + OCR
                  │                 │                 │
                  └─────────────────┴─────────────────┘
                                    │
                                    ▼
                           ┌─────────────────┐
                           │   Input Router  │
                           └────────┬────────┘
                                    │
                         ┌──────────┴──────────┐
                         │                     │
                         ▼                     ▼
                  LLM Code Synthesis       Existing Code
                         │                     │
                         └──────────┬──────────┘
                                    ▼
                         ┌─────────────────────┐
                         │ Dependency Analysis │
                         └──────────┬──────────┘
                                    ▼
                     ┌────────────────────────────┐
                     │     Static Analysis        │
                     │ Bandit | Pylint | Semgrep │
                     └─────────────┬──────────────┘
                                   │
                                   ▼
                         ┌─────────────────────┐
                         │ LLM-Assisted Fixing │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │ Controlled Execution│
                         └──────────┬──────────┘
                                    │
                          ┌─────────┴─────────┐
                          │                   │
                       Success              Failure
                          │                   │
                          │                   ▼
                          │            LLM Debugging
                          │                   │
                          │                   ▼
                          │            Auto-Fix Attempt
                          │
                          └──────────┬────────┘
                                     ▼
                           ┌───────────────────┐
                           │ Test Generation   │
                           │     + Pytest      │
                           └─────────┬─────────┘
                                     ▼
                           ┌───────────────────┐
                           │ Unified Reporting │
                           └───────────────────┘
```

---

# 🔄 End-to-End Pipeline

The framework executes a multi-stage processing pipeline.

### 1. Route Input

The input router determines whether the request contains:

```text
TEXT_PROMPT
CODE_INPUT
IMAGE_UPLOAD
EMPTY
UNKNOWN
```

---

### 2. Generate or Extract Code

Depending on the input:

**Text Prompt**

```text
Natural Language
      ↓
Groq LLM
      ↓
Python Code
```

**Paste Code**

```text
Existing Python Code
      ↓
Direct Analysis
```

**Image Upload**

```text
Code Screenshot
      ↓
Image Preprocessing
      ↓
Tesseract OCR
      ↓
Extracted Text
      ↓
Code Analysis
```

---

### 3. Analyze Dependencies

The dependency analyzer inspects imports and determines whether required modules appear to be available.

---

### 4. Run Static Analysis

The code is analyzed using:

```text
Bandit
Pylint
Semgrep
```

---

### 5. Apply Automated Remediation

If security or quality issues are detected, the framework can invoke LLM-assisted remediation.

The resulting code is analyzed again.

---

### 6. Execute Code

The framework runs the code using controlled subprocess execution with a timeout.

---

### 7. Debug Runtime Failures

If execution fails:

```text
Runtime Error
     ↓
Error Extraction
     ↓
LLM Explanation
     ↓
LLM-Assisted Fix
```

---

### 8. Generate Tests

The LLM generates a Pytest suite based on the analyzed code.

---

### 9. Execute Tests

The generated tests are executed using Pytest.

---

### 10. Build Unified Report

All results are consolidated into a structured report for presentation through the Streamlit UI.

---

# 🧩 Project Structure

```text
securecode-ai/
│
├── app.py
│
├── modules/
│   ├── __init__.py
│   ├── code_synthesis.py
│   ├── debugger.py
│   ├── dynamic_analysis.py
│   ├── llm_core.py
│   ├── pipeline.py
│   ├── static_analysis.py
│   └── test_generator.py
│
├── utils/
│   ├── dependency_manager.py
│   ├── dependency_policy.py
│   ├── image_processor.py
│   ├── input_router.py
│   ├── report_builder.py
│   └── sandbox.py
│
├── .streamlit/
│   └── config.toml
│
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

# 📁 Module Responsibilities

| Module                        | Responsibility                                    |
| ----------------------------- | ------------------------------------------------- |
| `app.py`                      | Streamlit user interface and result presentation  |
| `modules/pipeline.py`         | End-to-end pipeline orchestration                 |
| `modules/llm_core.py`         | Groq LLM client abstraction and response handling |
| `modules/code_synthesis.py`   | Code generation and LLM-assisted code fixing      |
| `modules/debugger.py`         | Runtime-error explanation and debugging workflow  |
| `modules/dynamic_analysis.py` | Dynamic execution interface                       |
| `modules/static_analysis.py`  | Bandit, Pylint, and Semgrep integration           |
| `modules/test_generator.py`   | LLM test generation and Pytest execution          |
| `utils/input_router.py`       | Input classification and routing                  |
| `utils/image_processor.py`    | Image preprocessing and OCR extraction            |
| `utils/dependency_manager.py` | Dependency/import analysis                        |
| `utils/dependency_policy.py`  | Dependency handling policy                        |
| `utils/sandbox.py`            | Controlled subprocess execution                   |
| `utils/report_builder.py`     | Unified report construction                       |

---

# 🛠️ Technology Stack

## Application

* Python
* Streamlit

## Artificial Intelligence

* Groq API
* LLM-assisted code synthesis
* LLM-assisted code remediation
* LLM-assisted debugging
* LLM-generated tests

## Security & Static Analysis

* Bandit
* Pylint
* Semgrep

## Testing

* Pytest

## Image Processing & OCR

* Pillow
* pytesseract
* Tesseract OCR

## Configuration

* python-dotenv

---

# 🚀 Getting Started

## Prerequisites

Before running SecureCode AI, install:

* Python 3.10+
* Git
* Tesseract OCR
* Semgrep
* A Groq API key

Verify Python:

```bash
python --version
```

Verify Git:

```bash
git --version
```

Verify Tesseract:

```bash
tesseract --version
```

Verify Semgrep:

```bash
semgrep --version
```

---

# 📥 Installation

Clone the repository:

```bash
git clone https://github.com/prasadnikam2005/securecode-ai.git
cd securecode-ai
```

Create a virtual environment:

### Windows

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

---

# 🔑 Environment Configuration

Create a `.env` file in the project root.

Use `.env.example` as the template:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-120b
GROQ_MAX_TOKENS=2048
```

Never commit `.env` to Git.

The repository includes `.gitignore` rules to prevent environment secrets from being committed.

---

# ▶️ Run the Application

From the project root:

```bash
streamlit run app.py
```

The application will open in the browser.

The interface provides:

```text
Text Prompt
Paste Code
Image Upload
```

Select an input mode, provide the required input, and click:

```text
🚀 Run SecureCode Pipeline
```

---

# 🧪 Example Workflow

## Example: Analyze Existing Python Code

Input:

```python
def greet(name):
    print("Hello", name)

greet("Prasad")
```

The pipeline can process the code through:

```text
Input
 ↓
Dependency Analysis
 ↓
Bandit
 ↓
Pylint
 ↓
Semgrep
 ↓
Execution
 ↓
Generated Tests
 ↓
Pytest
 ↓
Unified Report
```

The application exposes the resulting analysis through:

* Original/Input Code
* Fixed Code
* Static Analysis
* Dependency Report
* Pytest Results
* Bug Explanation
* Raw Unified Report JSON

---

# 🖼️ Image-Based Workflow

A screenshot containing source code can be uploaded through **Image Upload**.

```text
Screenshot
    ↓
Pillow
    ↓
Image Preprocessing
    ↓
Tesseract OCR
    ↓
Text Cleanup
    ↓
Code Candidate
    ↓
SecureCode Pipeline
```

For best results:

* Use high-resolution screenshots.
* Keep the code clearly visible.
* Avoid excessive background content.
* Prefer dark-on-light or light-on-dark high-contrast code.
* Avoid screenshots containing multiple unrelated windows.
* Review OCR output before relying on it for execution.

---

# 🔐 Security Design Considerations

SecureCode AI is designed around a **defense-in-depth analysis workflow** rather than relying on a single mechanism.

### Multiple Analysis Layers

```text
LLM
 ↓
Bandit
 ↓
Pylint
 ↓
Semgrep
 ↓
Dependency Analysis
 ↓
Runtime Execution
 ↓
Pytest
```

Each layer provides a different type of signal.

### Secret Handling

API credentials are loaded through environment variables:

```python
os.getenv("GROQ_API_KEY")
```

Secrets are intentionally excluded from version control.

The repository provides:

```text
.env.example
```

rather than a real credential file.

### Timeout-Based Execution Control

The execution pipeline uses explicit timeouts to prevent indefinitely running processes.

Current defaults:

```text
Execution timeout: 10 seconds
Pytest timeout:    30 seconds
```

### Important Security Limitation

SecureCode AI should **not** be described as a fully isolated security sandbox.

The current implementation uses subprocess-based execution with timeouts. It does not provide complete operating-system, container, VM, network, filesystem, or privilege isolation.

For production deployment involving genuinely untrusted code, stronger isolation mechanisms should be added.

---

# ⚠️ Current Limitations

SecureCode AI is an engineering prototype/framework and has several areas that can be improved.

### OCR Accuracy

OCR can lose source-code formatting, especially indentation-sensitive formatting.

Python indentation may therefore require post-processing or manual verification.

### LLM Reliability

LLM-generated code, fixes, explanations, and tests can contain mistakes.

The framework therefore combines LLM output with static analysis and test execution rather than treating LLM output as automatically correct.

### Generated Test Quality

Generated tests may contain incorrect assumptions or assertions.

A failing generated test does not automatically prove that the application code is incorrect.

### Sandbox Isolation

The current execution mechanism is subprocess-based rather than a hardened security sandbox.

### Static Analysis Coverage

Bandit, Pylint, and Semgrep provide valuable analysis but cannot prove that code is secure or bug-free.

### Dependency Detection

AST-based import analysis is useful for identifying dependency candidates but cannot perfectly model every dynamic import or runtime dependency mechanism.

---

# 📈 Example Output Metrics

A pipeline execution can expose metrics such as:

```text
Static Issues
Bandit Issues
Semgrep Findings
Pylint Score
Pytest Passed
Pytest Failed
Pytest Skipped
Missing Dependencies
```

This provides a compact overview while detailed results remain available in the corresponding report sections.

---

# 🔬 Engineering Approach

The project follows several engineering principles:

### Separation of Concerns

The UI, pipeline orchestration, LLM integration, static analysis, OCR, dependency analysis, execution, testing, and reporting are separated into dedicated modules.

### Tool-Assisted Validation

Instead of relying exclusively on an LLM:

```text
LLM
+
Static Analysis
+
Dependency Analysis
+
Dynamic Execution
+
Automated Testing
```

are combined into a single workflow.

### Structured Results

Pipeline stages return structured information that can be aggregated into a unified report.

### Failure-Aware Processing

The pipeline attempts to distinguish:

* Successful execution
* Dependency-related problems
* Runtime failures
* Test failures
* LLM failures
* Partial completion

rather than assuming every pipeline execution succeeds.

---

# 🗺️ Future Improvements

Potential future enhancements include:

* [ ] Improved OCR formatting and indentation recovery
* [ ] Better code-language detection
* [ ] Multi-language source-code support
* [ ] Stronger Semgrep error handling
* [ ] Generated-test validation and self-correction
* [ ] Test quality scoring
* [ ] Containerized execution isolation
* [ ] Network-access restrictions for executed code
* [ ] Resource limits for CPU and memory
* [ ] More advanced dependency resolution
* [ ] Security finding severity dashboards
* [ ] Persistent analysis history
* [ ] Exportable HTML/PDF reports
* [ ] CI/CD integration
* [ ] GitHub repository scanning
* [ ] Pull-request security analysis
* [ ] Authentication and multi-user support
* [ ] Code-language-specific analysis pipelines

---

# 🎯 Project Objectives

The primary objectives of SecureCode AI are to explore how LLMs can be integrated into a **security-aware software development workflow** while maintaining additional validation layers.

The project focuses on:

1. **AI-assisted code generation**
2. **Security-oriented static analysis**
3. **Automated remediation**
4. **Runtime debugging**
5. **Automated test generation**
6. **Dependency inspection**
7. **Multimodal code extraction**
8. **Unified developer feedback**

The central idea is:

> **Use LLMs for generation and reasoning, but use deterministic developer tools and execution-based validation to provide additional evidence about the resulting code.**

---

# 📚 Technical Concepts Demonstrated

This project demonstrates practical implementation of:

* Large Language Model APIs
* Prompt engineering
* LLM orchestration
* Multimodal input handling
* OCR
* Static application security testing (SAST)
* Automated code remediation
* AST-based dependency analysis
* Dynamic program execution
* Runtime debugging
* Automated test generation
* Pytest integration
* Structured reporting
* Environment-based secret management
* Modular Python architecture
* Streamlit application development

---

# 👨‍💻 Author

**Prasad Nikam**

Computer Science Engineering — Artificial Intelligence & Machine Learning

GitHub:

`https://github.com/prasadnikam2005`

---

# 📄 License

This project is currently provided as a portfolio/engineering project.

A formal open-source license can be added separately depending on the intended distribution and usage requirements.

---

# ⭐ Project Summary

**SecureCode AI** demonstrates a practical approach to combining **LLM-based software engineering capabilities with traditional security and testing tools**.

Rather than treating an LLM as the sole source of truth, the framework creates a multi-stage workflow:

```text
          ┌────────────────────┐
          │ Human / Application│
          │       Input        │
          └─────────┬──────────┘
                    ↓
          ┌────────────────────┐
          │ LLM / OCR / Router │
          └─────────┬──────────┘
                    ↓
          ┌────────────────────┐
          │ Static Analysis    │
          │ Bandit/Pylint/     │
          │ Semgrep            │
          └─────────┬──────────┘
                    ↓
          ┌────────────────────┐
          │ LLM-Assisted       │
          │ Remediation        │
          └─────────┬──────────┘
                    ↓
          ┌────────────────────┐
          │ Dependency +       │
          │ Runtime Analysis   │
          └─────────┬──────────┘
                    ↓
          ┌────────────────────┐
          │ Test Generation +  │
          │ Pytest Validation  │
          └─────────┬──────────┘
                    ↓
          ┌────────────────────┐
          │ Unified Engineering│
          │ Report             │
          └────────────────────┘
```

The result is a modular experimentation platform for investigating how **generative AI, application security tooling, automated testing, and developer feedback loops** can work together in a single software-engineering workflow.
