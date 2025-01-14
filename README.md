---
language:
- en
tags:
- resume
- extractor
- resume extractor
- pdf
- extract
- cv parser
- pdf extraction
- document analysis
- unstructured document
- DataProcessing
- TextToJSON
- resume parser
- resume information extractor
- resume data extraction
---

# PDF Resume Information Extractor

## Description

This Python script extracts information from PDF resumes and converts it into a structured JSON format using the Ollama language model. It's designed to automate the process of parsing resumes and extracting key details, making it easier for HR departments, recruiters, and organizations to process large volumes of applications efficiently.

What sets this script apart is its ability to handle various resume formats and styles. It uses a predefined JSON template to ensure consistent output structure, making it easier to integrate with other systems or databases. The script is designed to be flexible, allowing for customization of the output format and the underlying language model.

We invite you to explore the potential of this script and its data extraction capabilities. For those interested in harnessing its power or seeking further collaboration, we encourage you to reach out to us or contribute to the project on GitHub. Your input drives our continuous improvement, as we collectively pave the way towards enhanced data extraction and document analysis.

- **Developed by:** FODUU AI
- **Model type:** Extraction
- **Task:** Resume Parsing and Information Extraction

### Supported Output Fields

The exact fields depend on the JSON template which have includes the following fields:
['name', 'email', 'phone_1', 'phone_2', 'address', 'city', 'highest_education', 'is_fresher','is_student', 'professional_experience_in_years', 'skills' ,'linkedin' , 'applied_for_profile', 'education', 'professional_experience']


## Uses

### Direct Use

The Resume Information Extractor can be directly used for parsing resume PDFs and extracting structured information. It's particularly useful for HR departments, recruitment agencies, or any organization that deals with large volumes of resumes.

### Downstream Use

The extracted information can be used for various downstream tasks such as candidate matching, resume scoring, or populating applicant tracking systems.

### Out-of-Scope Use

The model is not designed for tasks unrelated to resume parsing or for processing documents that are not resumes.

## Risks, and Limitations

The Resume Information Extractor may have some limitations and risks, including:

- Performance may vary based on the format and structure of the input resume.
- The quality of extraction depends on the capabilities of the underlying Ollama model.
- It may struggle with highly unconventional resume formats or non-English resumes.
- The script does not verify the accuracy of the information in the resume.

### Recommendations

Users should be aware of the script's limitations and potential risks. It's recommended to manually verify the extracted information for critical applications. Further testing and validation are advised for specific use cases to evaluate its performance accurately.

## How to Get Started with the Model

To begin using the Resume Information Extractor, follow these steps:

1. Clone this repository:

   ```bash
   git clone https://huggingface.co/nehulagrawal/resume-extractor
   ```

2. Install the required packages:
   ```bash
   pip install langchain_community pdfminer.six ollama
   ```

   or

   ```bash
   pip install -r requirements.txt
   ```


3. Ensure you have Ollama set up and running with the "llama3" model.

4. Use this Python script:

```python
from pdfminer.high_level import extract_text
from json_helper import InputData as input

def extract_text_from_pdf(pdf_path):
    return extract_text(pdf_path)

text = extract_text_from_pdf(r'path/to/your/document/pdf')

llm = input.llm()
data = llm.invoke(input.input_data(text))

print(data)
```

## Objective

This script uses the Ollama language model to understand and extract information from resume text. The specific architecture depends on the Ollama model being used.


## Contact

For inquiries and contributions, please contact us at info@foduu.com.

```bibtex
@contact{foduu,
  author    = {Foduu},
  title     = {Resume Extractor},
  year      = {2024}
}

```