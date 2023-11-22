import os
import pyodbc
import json
import azure.functions as func
import logging

from sqlalchemy import create_engine

from langchain.chat_models import AzureChatOpenAI
from langchain.prompts.chat import ChatPromptTemplate
from langchain.agents import AgentType, create_sql_agent
from langchain.sql_database import SQLDatabase
from langchain.agents.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_experimental.sql import SQLDatabaseChain

### ENV ###


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    input = req.params.get('input')
    if not input:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            input = req_body.get('input')

    if input:

        driver = 'ODBC Driver 18 for SQL Server'
        odbc_str = 'mssql+pyodbc:///?odbc_connect=' \
                        'Driver='+driver+ \
                        ';Server=tcp:' + os.getenv("SQL_SERVER")+'.database.windows.net;PORT=1433' + \
                        ';DATABASE=' + os.getenv("SQL_DB") + \
                        ';Uid=' + os.getenv("SQL_USERNAME")+ \
                        ';Pwd=' + os.getenv("SQL_PWD") + \
                        ';Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;'

        db_engine = create_engine(odbc_str)

        llm = AzureChatOpenAI(#model=os.getenv("OPENAI_CHAT_MODEL"),
                            deployment_name=os.getenv("OPENAI_CHAT_MODEL"),
                            #azure_endpoint=os.getenv("OPENAI_API_BASE"),
                            temperature=0)

        db = SQLDatabase(db_engine)

        sql_toolkit = SQLDatabaseToolkit(db=db, llm=llm)
        sql_toolkit.get_tools()

        db_chain = SQLDatabaseChain.from_llm(
            llm, 
            db, 
            verbose=True,    
            return_intermediate_steps=True
            )
           
        response = get_query_and_result(chain = db_chain, input = input)
        logging.info(response)
        return func.HttpResponse(response)
    
    else:
        return func.HttpResponse(
             "This HTTP triggered function executed successfully without input."
        )

def get_query_and_result(chain, input):

    out = chain(input)
    sql_query = out['intermediate_steps'][1]
    response = out['result'].split("\n")[0]
    out_dict = {'sql_query': sql_query, 'response': response}
    
    return json.dumps(out_dict)