import streamlit as st
import time
from PIL import Image
from ddgs import DDGS
import wikipediaapi
from google import genai
from google.genai import types
from google.genai import errors
from anthropic import Anthropic
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.rl_config import defaultPageSize
from reportlab.lib.units import inch
from io import BytesIO
from xhtml2pdf import pisa
import markdown
from tika import parser
from tavily import TavilyClient, TavilyKeylessLimitError

# Loading Image using PIL
im = Image.open('browser_logo.png')
# Adding Image to web app
st.set_page_config(page_title="Company History Research App", page_icon = im)


if "urls" not in st.session_state:
    st.session_state.urls = []

if "response_text" not in st.session_state:
    st.session_state.response_text = None

if "params_valid" not in st.session_state:
    st.session_state.params_valid = True


st.image("company_logo.png", width=300)  # width is optional, controls display size

company_name = st.text_input("Enter Company Name: ", value = "Montanaro Asset Management")

max_resources = st.number_input("Enter the maximum number of resources you would like DDGS to use: ",
            min_value = 10,
            step = 1,
            value = 20,
    )
gemini_api_key_input = st.text_input("Gemini API-key: ",
            placeholder = "Enter your Gemini API key here",
            type = "password",
)   

tav_api_key_input = st.text_input("Tavily API-key: ",
            placeholder = "Enter your Tavily API key here (Optional)",
            type = "password",
)   
st.toast('The Tavily API key is optional but recommended for better results',
         icon = 'ℹ️',
        duration = 6
)

model_select = st.selectbox(
    "Which Gemini model would you like to use?",
    ("gemini-3.6-flash","gemini-3.5-flash","gemini-3.1-flash-lite",
     "gemini-2.5-flash-lite"
)
)

def parameter_checker(company = company_name, api = gemini_api_key_input):
    st.session_state.params_valid = True
    if company.strip() == "":
        st.error("Please Enter Company Name")
        st.session_state.params_valid = False
 
    if api =="":
        st.error("Please Enter Gemini API-key")
        st.session_state.params_valid = False


#import time

#t0 = time.time()


button = st.button("Run Research", type = "primary",on_click = parameter_checker)

get_api = st.link_button("Get your Gemini API key", "https://aistudio.google.com/app/apikey")

get_tavily_api = st.link_button("Get your Tavily API key", "https://app.tavily.com/home")

focus_points = st.text_area("Specific areas to focus on (Optional)")

uploaded_file = st.file_uploader("Upload Extra Information Here (Optional)",accept_multiple_files = True)
extracted_text = []
contents = []
for file in uploaded_file:
        
    if file is not None:
        file_bytes = file.read()
        parsed_data = parser.from_buffer(file_bytes)
        extracted_text.append(parsed_data.get('content',""))
        contents.append(extracted_text)
    else:
        extracted_text = None

if button and st.session_state.params_valid:
    



    wiki_wiki = wikipediaapi.Wikipedia(user_agent = 'Company History Research Tool (yonisabdiaziz05@gmail.com)', language = 'en')
    page_py = wiki_wiki.page(company_name)
    st.write('Wikipedia Page - Exists: %s' % page_py.exists())
    
    

    #page_missing = wiki_wiki.page('NonExistingPageWithStrangeName')
    #print('Page - Missing: %s' %page_missing.exists())
    st.write("---")

    #print('Page - Title: %s' %page_py.title)

    #print('Page - Text: %s' %page_py.text)

    if page_py.exists() == False:
        st.write(f"{company_name} not found on Wikipedia")
        st.write("---")
        st.write("Checking elsewhere...")
        

    try:
        results = DDGS().text(company_name,max_results=max_resources)
        #st.write(f"Got {len(results)} results")
        #print(results)
    except Exception as e:
        st.write(f"Error type: {type(e).__name__}")
        st.write(f"Error message: [e]")

    urls = []
    st.write("Storing URLs...")
    
    
    for r in results:
        urls.append(r["href"])
    st.write("Stored URLs")
    #st.write("---")
    contents.append(urls)
    try: 
        client_tav = TavilyClient(api_key=tav_api_key_input)
        
        client_tav.session.verify = False
        
        optimized_query = f"{company_name} official corporate profile overview background history"
        
        response = client_tav.search(optimized_query,
                                max_results = 20)
    
        just_urls = [result["url"] for result in response.get("results", [])]
        
     
        urls.extend(just_urls)
    except:
        pass

    st.write(f"Found {len(urls)} results")
    st.write("---")
    
    import trafilatura

    info = []
    st.write("Downloading information from URLs...")
    
    
    info.append(page_py.text)
    for link in urls:
        downloaded = trafilatura.fetch_url(link)
        paragraph = trafilatura.extract(downloaded)
        info.append(paragraph)

    st.write("Downloaded information")
    st.write("---")
    st.write("Cleaning text...")
    
    
    info_cleaned = [text for text in info if text is not None]
    info_cleaned_text = "\n".join(info_cleaned)
    st.write(f"Cleaned text and got {len(info_cleaned_text)} characters")
    st.write("---")
    contents.append(info_cleaned_text)


    
    response = None
    try:


        client = genai.Client(api_key=gemini_api_key_input)
        st.write("Summarising text...")
        
        
        st.write("---")
        system_prompt = f"""You are a corporate analyst investigating the company: {company_name}.

       Review the provided text and extract the details below.
        CRITICAL: If the source text does not contain the information,
        simply output "N/A". Number your sources like [1],[2] etc chronologically
        (This is VITAL). At the end before confidence score justification i need you
        to use the url list i gave you and bullet point list the sources you used in the
        report. Include a link to the source next to each bullet point in the
        "Sources Used" section and make sure if something appears in that section then it
        was used in the report. If multiple sources were used for a sentence/paragraph then
        you may combine them like this [1,2] with a comma signifying both source [1] and [2]
        were used there. Then give a small to medium lengthed justification
        as to why you have not used all the sources provided (if that's the case). 


        
        Provide details on:
        1. Founding: When, where, and by whom.
        2. Evolution: Original business vs. how it developed.
        3. Major Changes: Shifts in products, services, customers, or geography.
        4. Corporate Actions: Acquisitions, disposals, mergers, or restructurings.
        5. Ownership: Ownership changes or stock-market listings.
        6. Strategy: Significant strategic decisions or changes in direction.
        7. Milestones/Crises: Periods of major success, difficulty, or controversy.
        8. Current State: What it does today and where it is headquartered.
        9. Management: Background and tenure of the current senior management team.
        10. Investor Context: Historical events most relevant to an investor today.

        Important requirements
        The report should:
        1. Be analytical rather than promotional.
        It should explain why important events matter, rather than simply repeating the company's description of them

        2. Separate fact from interpretation.
        The reader should be able to distinguish factual corporate history from conclusions generated by Claude

        3. Use reliable sources.
        Important statements should be accompanied by links or clear references to their orignial surces. Company claims should be
        checked against independent or regulatory sources where possible.

        4. Avoid false precision.
        Where information is uncertain, disputed or unavailable, the report should say so rather than guessing.

        5.Be concise enough to use.
        An analyst should be able to read the report reasonably quickly while still gaining a meaningful understanding of the company

        6. Work across different kinds of company.
        Consider whether the same approach would work for an established industrial business, a technology company and a business that
        has grown substantially through acquisitions.

        End your response strictly with: "Confidence Score: [0-100]% and give a short justification on why the score is the way it is.
        If the user has provided any specific focus points, obey them with top priority. 
        Here are the focus points: {focus_points}. 

        CRITICAL FILE HANDLING: You have been provided an uploaded document under the variable 'extracted_text'. 
        Analyze this document. If the document is about a completely different company than {company_name}, 
        DO NOT mix its data into the history of {company_name}. Instead, follow the user's focus point 
        instructions exactly and clearly state what company or topic the uploaded file actually contains 
        at the very beginning or end of your response as requested.\""""


        response = client.models.generate_content(
            model = model_select,
            config = types.GenerateContentConfig(
                system_instruction = system_prompt
            ),
            contents=contents
        )
        st.write("Summarised Text")
        #st.write(response.text)
    except errors.APIError as e:
        if e.code == 429:
            st.error(f"You've hit Gemini's rate/quota limit using {model_select}. Please wait a minute and try again, or check your usage at https://aistudio.google.com/app/rate-limit. If it's still not working then consider switching to another model")
        elif e.code >= 500:
            st.error("Gemini is experiencing issues right now. Please try again later")
        else:
            st.error("Something unexpected went wrong. Please try again later")
        st.write(e.code)
        st.write(e.message)





    st.session_state.urls = urls
    st.session_state.response_text = response.text
    
if st.session_state.response_text is not None:               
    button_sources = st.button("See Sources")
    #t1 = time.time()
    #total_time = t1-t0
    #rounded_time = round(total_time,2)
    #formatted_time = f"{rounded_time:,}"
    if button_sources:
        #st.write(f"This took {formatted_time}s to run")
        st.write(f"Number of sources used: {len(st.session_state.urls)}")
        st.write("See all sources below:")
        for url in st.session_state.urls:
            st.write(url)


    PAGE_HEIGHT=defaultPageSize[1]; PAGE_WIDTH=defaultPageSize[0]
    styles = getSampleStyleSheet()

    def build_pdf(comapny_name, text):
        html = markdown.markdown(text)
        full_html = f"<h1>{company_name} - Company History Report</h1>{html}"
        buffer = BytesIO()
        pisa.CreatePDF(full_html, dest=buffer)
        buffer.seek(0)
        return buffer
    if st.session_state.response_text is not None:
        pdf_buffer = build_pdf(company_name, st.session_state.response_text)
        st.download_button(
            label = "Download as pdf",
            data = pdf_buffer,
            file_name = f"{company_name} -- Report.pdf",
             mime = "application/pdf"
        )
    else:
        st.error("No report was generated, so no PDF is available to download")
#st.write(extracted_text)
