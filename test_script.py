
import os
#from dotenv import load_dotenv
import json

from sqlalchemy import create_engine
import pyodbc

from langchain.chat_models import AzureChatOpenAI
from langchain.prompts.chat import ChatPromptTemplate
from langchain.agents import AgentType, create_sql_agent
from langchain.sql_database import SQLDatabase
from langchain.agents.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_experimental.sql import SQLDatabaseChain


driver = 'ODBC Driver 18 for SQL Server'
odbc_str = 'mssql+pyodbc:///?odbc_connect=' \
                'Driver='+driver+ \
                ';Server=tcp:' + os.getenv("SQL_SERVER")+'.database.windows.net;PORT=1433' + \
                ';DATABASE=' + os.getenv("SQL_DB") + \
                ';Uid=' + os.getenv("SQL_USERNAME")+ \
                ';Pwd=' + os.getenv("SQL_PWD") + \
                ';Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;'

db_engine = create_engine(odbc_str)


llm =   AzureChatOpenAI(
            deployment_name=os.getenv("OPENAI_CHAT_MODEL"),
            temperature=0)

db = SQLDatabase(db_engine)

sql_toolkit = SQLDatabaseToolkit(db=db, llm=llm)
sql_toolkit.get_tools()


q = "How are the different event types distributed?"

# method 1
sqldb_agent = create_sql_agent(
    llm=llm,
    toolkit=sql_toolkit,
    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    handle_parsing_errors=True,
    return_intermediate_steps=True,
)

out = sqldb_agent.run(q)
print(out)

# method 2
db_chain_1 = SQLDatabaseChain.from_llm(
    llm, 
    db, 
    verbose=True,    
    #return_intermediate_steps=True
    )
out = db_chain_1(q)
out = out.split("Question")[0].split("\n")[0]
print(out)


# method 3 - return tuple w intermediate steps
db_chain_2 = SQLDatabaseChain.from_llm(
    llm, 
    db, 
    verbose=True,    
    return_intermediate_steps=True
    )
out = db_chain_2(q)

sql_query = out['intermediate_steps'][1]
response = out['result'].split("\n")[0]






def get_query_and_result(chain, question):
    out = chain(question)
    sql_query = out['intermediate_steps'][1]
    response = out['result'].split("\n")[0]
    out_dict = {'sql_query': sql_query, 'response': response}
    
    return json.dumps(out_dict)

json_output = get_query_and_result(chain = db_chain_2, question = q)

# not working
#sqldb_agent.run(final_prompt.format(question=q))


final_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", 
         """
         You are a helpful AI assistant expert in identifying the relevant information to answer the user's question. Context: The data consist of user events with columns that denote the user id, user type, event type and time of event.
        """
         ),
        ("user", "{question}\n ai: "),
    ]
)

''' about users and events and then querying SQL Database table called 'events' to find answer.
         Use following context to create the SQL query. Context:
        The 'events' table contains information about users and events based on user behaviour.
        The userID column identifies users.
        The userType column shows the user type.
        the time column has a timestamp.
        the event column has infomation about event type.'''