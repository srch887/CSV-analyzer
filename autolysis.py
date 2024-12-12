# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "numpy",
#   "pandas",
#   "requests",
#   "python-dotenv",
#   "seaborn",
#   "matplotlib",
#   "rich",
#   "ipykernel"
# ]
# ///

import numpy as np
import pandas as pd
import seaborn
import matplotlib.pyplot
import json
import os
import sys
import requests
from io import StringIO
from dotenv import load_dotenv

load_dotenv()

# Load token from .env file
token = os.environ["AIPROXY_TOKEN"]

if(not token):
    print("Error: Couldn't read AI Proxy Token")
    print(token)
    sys.exit(1)

LLM_URL = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"

LLM_HEADER = {"Authorization": f"Bearer {token}"}

# Capture basic information regarding the dataset like dimensions, column names, datatypes and null value count
def capture_info(dataframe):
    info_dict = {
        "num_rows": len(dataframe),
        "num_columns": len(dataframe.columns),
        "columns": []
    }
    
    for column in dataframe.columns:
        col_data = {
            "name": column,
            "dtype": str(dataframe[column].dtype),
            "non_null_count": int(dataframe[column].notnull().sum()),
            "null_count": int(dataframe[column].isnull().sum())
        }
        info_dict["columns"].append(col_data)
        
    return info_dict

# Read csv file and generate summary
def analyze_csv(file_path):
    print(f"Loading data from {file_path}...")
    data = pd.read_csv(file_path, encoding = "ISO-8859-1")
    
    # Converting int64 to int as object of type int64 is not JSON serializable
    data = data.apply(lambda x: int(x) if isinstance(x, np.int64) else x)
    
    # Summary statistics and basic info
    summary = {
        "columns": list(data.columns),
        "info": capture_info(data)
    }
    
    return data, summary

# Generate insights with the help of an LLM using the summary
def ask_llm_for_insights(summary):
    print("Generating insights...")

    try:
        response = requests.post(
            url=LLM_URL,
            headers=LLM_HEADER,
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "Analyze the following dataset summary and provide key insights. Write the output in markup format so that it can be properly viewed in a .md file"},
                    {"role": "user", "content": str(summary)}
                ]
            }
        )
        
        result = response.json()
        
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Error communicating with LLM: {e}")
        return "No insights available."
    
# Using an LLM to generate python code to create a correlation matrix heatmap
def generate_code_corr_matrix(file_name_without_extension):
    print("Generating correlation matrix heatmap...")
    
    try:
        response = requests.post(
            url=LLM_URL,
            headers=LLM_HEADER,
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are to generate a python code for the given task. Only output the code and nothing else. The code is run in an interperter so do not add the \"python\" command in the front."},
                    {"role": "user", "content": "Generate python code to generate a correlation heatmap for a pandas dataframe named df using the seaborn library and save it in the \"./{}\" folder in png format. Make the folder if it does not exist. Make sure to consider only numeric data for calculations. Don't try to visualize the graph as the code is not running in a jupyter notebook. Just save the file.".format(file_name_without_extension, str(summary))}
                ]
            }
        )
        
        result = response.json()
        
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Error communicating with LLM: {e}")
        return "No insights available."
    
# Using an LLM to generate python code to create a bar chart showing all null value counts
def generate_missing_value_graph(file_name_without_extension):
    print("Generating graph to count missing values...")
    
    try:
        response = requests.post(
            url=LLM_URL,
            headers=LLM_HEADER,
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are to generate a python code for the given task. Only output the code and nothing else. The code is run in an interperter so do not add the \"python\" command in the front."},
                    {"role": "user", "content": "Generate python code to generate a bar chart for showing the number of missing values for a pandas dataframe named df using the seaborn library and save it in the \"./{}\" folder in png format. Make the folder if it does not exist. The dataframe is already loaded so just provide the remaining code. Don't try to visualize the graph as the code is not running in a jupyter notebook. Just save the file.".format(file_name_without_extension)}
                ]
            }
        )
        
        result = response.json()
        
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Error communicating with LLM: {e}")
        return "No insights available."
    
# Using an LLM to generate python code to create histograms for all columns. Ignore columns with more than 25 categories
def generate_histograms(file_name_without_extension):
    print("Generating histograms for all columns...")
    
    try:
        response = requests.post(
            "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are to generate a python code for the given task. Only output the code and nothing else. The code is run in an interperter so do not add the \"python\" command in the front."},
                    {"role": "user", "content": "You have a dataframe df. Generate the code to plot the histograms of all individual columns and show them in a single image as tiles  using the seaborn and matplotlib libraries. Treat categorical and numerical columns accordingly. Ignore columns that have more than 25 categories altogether(No need to show any message). Save the plot in the \"./{}\" folder in png format. Make the folder if it does not exist. The dataframe is already loaded so just provide the remaining code.  Don't try to visualize the graph as the code is not running in a jupyter notebook. Just save the file.".format(file_name_without_extension)}
                ]
            }
        )
        
        result = response.json()
        
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Error communicating with LLM: {e}")
        return "No insights available."
    
# Output all insights into a readme file
def create_readme(insights, output_dir):
    """Generates a Markdown file with insights and visualizations."""
    
    output_file = "./" + output_dir + "/README.md"
    
    with open(output_file, "w") as f:
        f.write(insights)
    
# Main function call
    
if __name__ == "__main__":
    # Checking function call arguments
    if len(sys.argv) != 2:
        print("Usage: uv run autolysis.py <dataset.csv>")
        sys.exit(1)
        
    file_name = sys.argv[1]
    
    df, summary = analyze_csv(file_name)
        
    file_name_without_extension = os.path.splitext(file_name)[0]

    # Generating correlation heatmap
    corr_map_code = generate_code_corr_matrix(file_name_without_extension)
 
    try:
        exec(corr_map_code)
    except Exception as e:
        print(f"Error executing generated code: {e}")
        sys.exit(1)
        
    # Generating null value count graph
    missing_val_graph_code = generate_missing_value_graph(file_name_without_extension)
    
    try:
        exec(missing_val_graph_code)
    except Exception as e:
        print(f"Error executing generated code: {e}")
        sys.exit(1)
        
    # Generating histograms
    generate_histograms_code = generate_histograms(file_name_without_extension)
    
    try:
        exec(generate_histograms_code)
    except Exception as e:
        print(f"Error executing generated code: {e}")
        sys.exit(1)
        
    # Generating insights
    insights = ask_llm_for_insights(summary)
    
    create_readme(insights, file_name_without_extension)
    
    print("Analysis successful")
