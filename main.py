from flask import Flask, render_template, request
from markupsafe import escape
import os
import yaml
import vertexai
from typing import List

from google.api_core.client_options import ClientOptions
from google.cloud import discoveryengine_v1 as discoveryengine

####################################################################################
# Set the DATA_STORE_ID and PROJECT_ID variables for your project
####################################################################################
LOCATION = "global"
DATA_STORE_ID = "python-programming-data-st_1709560381748"
PROJECT_ID = "vertext-ai-dar"


app = Flask(__name__)

# Helper function that reads from the config file. 
def get_config_value(config, section, key, default=None):
    """
    Retrieve a configuration value from a section with an optional default value.
    """
    try:
        return config[section][key]
    except:
        return default

# Open the config file (config.yaml)
with open('config.yaml') as f:
    config = yaml.safe_load(f)

# Read application variables from the config fle
TITLE = get_config_value(config, 'app', 'title', 'Ask Google')
SUBTITLE = get_config_value(config, 'app', 'subtitle', 'Your friendly Bot')
CONTEXT = get_config_value(config, 'palm', 'context',
                           'You are a bot who can answer all sorts of questions')
BOTNAME = get_config_value(config, 'palm', 'botname', 'Google')
TEMPERATURE = get_config_value(config, 'palm', 'temperature', 0.8)
MAX_OUTPUT_TOKENS = get_config_value(config, 'palm', 'max_output_tokens', 256)
TOP_P = get_config_value(config, 'palm', 'top_p', 0.8)
TOP_K = get_config_value(config, 'palm', 'top_k', 40)


# The Home page route
@app.route("/", methods=['POST', 'GET'])
def main():
    responses = []

    # The user clicked on a link to the Home page
    # They haven't yet submitted the form
    if request.method == 'GET':
        search_query = ""

    # The user asked a question and submitted the form
    # The request.method would equal 'POST'
    else: 
        search_query = request.form['input']

        # Search the Data Storw passing in the user's question
        response = search_data_store(PROJECT_ID, LOCATION, DATA_STORE_ID, search_query)

        # The Response needs formatted to be displayed in the HTML template
        responses = format_response(response)

        
    # Display the home page with the required variables set
    model = {"title": TITLE, "subtitle": SUBTITLE,
             "botname": BOTNAME, "input": search_query, 
             "responses": responses}
    return render_template('index.html', model=model)

####################################################################################
#
# See the following URL for implementing this function
# https://cloud.google.com/generative-ai-app-builder/docs/preview-search-results#genappbuilder_search-python
#
####################################################################################
def search_data_store(
    project_id: str,
    location: str,
    data_store_id: str,
    search_query: str,
) -> List[discoveryengine.SearchResponse]:

    client_options = (
        ClientOptions(api_endpoint=f"{location}-discoveryengine.googleapis.com")
        if location != "global"
        else None
    )

    # Create a client
    client = discoveryengine.SearchServiceClient(client_options=client_options)

    serving_config = client.serving_config_path(
        project=project_id,
        location=location,
        data_store=data_store_id,
        serving_config="default_config",
    )

    content_search_spec = discoveryengine.SearchRequest.ContentSearchSpec(
        snippet_spec=discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(
            return_snippet=True
        ),
        summary_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec(
            summary_result_count=5,
            include_citations=True,
            ignore_adversarial_query=True,
            ignore_non_summary_seeking_query=True,
        ),
    )

    request = discoveryengine.SearchRequest(
        serving_config=serving_config,
        query=search_query,
        page_size=10,
        content_search_spec=content_search_spec,
        query_expansion_spec=discoveryengine.SearchRequest.QueryExpansionSpec(
            condition=discoveryengine.SearchRequest.QueryExpansionSpec.Condition.AUTO,
        ),
        spell_correction_spec=discoveryengine.SearchRequest.SpellCorrectionSpec(
            mode=discoveryengine.SearchRequest.SpellCorrectionSpec.Mode.AUTO
        ),
    )

    response = client.search(request)
    #print(response)

    return response


####################################################################################
#
# The discoveryengine.SearchResponse is Documented here:
# https://cloud.google.com/python/docs/reference/discoveryengine/latest/google.cloud.discoveryengine_v1.types.SearchResponse
#
# Hint 1: Return a collection of objects with the fields: title, snippet, and url
# Hint 2: To enumerate the results return in the response use the loop: for result in response.results
# Hint 3: In the loop, the following snippets will retrive the required data:
#    result.document.derived_struct_data["htmlTitle"]
#    result.document.derived_struct_data["snippets"][0]["htmlSnippet"]
#    result.document.derived_struct_data["snippets"][0]["htmlSnippet"]
#    
####################################################################################
def format_response(response):
    results = []
    for result in response.results:
        entry = {
            "title": result.document.derived_struct_data["htmlTitle"], 
            "snippet": result.document.derived_struct_data["snippets"][0]["htmlSnippet"],
            "url": result.document.derived_struct_data["formattedUrl"]
        }
        results.append(entry)
    
    return results

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
