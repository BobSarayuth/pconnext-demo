# import asyncio
# import csv
# import os
# from typing import Any, Dict, TypedDict

# import pandas as pd
# from dotenv import load_dotenv
# from langchain.output_parsers import PydanticOutputParser
# from langchain.prompts import ChatPromptTemplate
# from langchain_core.messages import HumanMessage
# from langchain_openai import ChatOpenAI
# from langgraph.checkpoint.memory import MemorySaver
# from langgraph.graph import END, StateGraph
# from pydantic import BaseModel, Field


# load_dotenv()


# # Define state structure
# class QAState(TypedDict):
#     question_answer: str
#     result: Dict[str, Any]


# # Define a Pydantic model for the structured output
# class QAConsistencyResult(BaseModel):
#     similar: str = Field(description="YES or NO indicating if answer is appropriate")
#     score: int = Field(description="Score from 1-5 for answer appropriateness")
#     reason: str = Field(description="Reason for the score, especially if score < 3")


# # Initialize LangChain ChatOpenAI
# llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# # Create a parser for structured output
# parser = PydanticOutputParser(pydantic_object=QAConsistencyResult)

# # Create a chat prompt template
# system_prompt = 'คุณมีหน้าที่ตรวจสอบว่า คำถาม และคำตอบสอดคล้องกันไหม ในรูปแบบ "คำถาม|คำตอบ" ตอบว่าสอดคล้องกัน หรือไม่สอดคล้องกัน โดยให้คะแนน 1-5 ด้วย ถ้าน้อยกว่า 3 ซึ่งไม่สอดคล้องกันให้เหตุผลสั้นได้ใจความ ถึงความไม่สอดคล้องกัน  ของสนทนานั้นด้วย ตอบเป็น JSON Structure มีที่ similar เป็น YES or NO และ reason เป็น เหตุผล และ score คือคะแนน'
# prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", "{qa_pair}")])


# # Function to evaluate question-answer consistency using LangChain
# def evaluate_qa_consistency(state: QAState) -> QAState:
#     """Evaluate if a question and answer are consistent using LangChain."""
#     qa_pair = state["question_answer"]

#     try:
#         # Create and run the LangChain chain
#         chain = prompt | llm | parser
#         result = chain.invoke({"qa_pair": qa_pair})
#         # Convert pydantic model to dict
#         result = result.model_dump()
#     except Exception as e:
#         # Fallback if parsing fails
#         result = {"similar": "ERROR", "score": 0, "reason": f"Error processing response: {str(e)}"}

#     state["result"] = result
#     return state


# # Define the LangGraph workflow
# def create_qa_evaluation_graph():
#     # Create a new graph
#     workflow = StateGraph(QAState)

#     # Add nodes to the graph
#     workflow.add_node("evaluate", evaluate_qa_consistency)

#     # Define the edges
#     workflow.add_edge("evaluate", END)

#     # Set the entry point
#     workflow.set_entry_point("evaluate")

#     # Compile the graph
#     return workflow.compile()


# def process_csv_file():
#     # Path to input and output files
#     input_file = "g:\\.scg-wedo\\digital-chatbot\\retest-result.csv"
#     output_file = "g:\\.scg-wedo\\digital-chatbot\\retest-result-q&a.csv"

#     # Read CSV file using pandas
#     df = pd.read_csv(input_file)

#     # Initialize QA evaluation graph
#     graph = create_qa_evaluation_graph()

#     # Add new columns for evaluation results
#     df["Similar"] = ""
#     df["Score"] = 0
#     df["Reason"] = ""

#     # Process each row
#     for index, row in df.iterrows():
#         # Skip rows where either query or answer is missing
#         if pd.isna(row["ActualQuery"]) or pd.isna(row["ActualAnswer"]):
#             continue

#         # Create the question_answer pair
#         qa_pair = f"{row['ActualQuery']}|{row['ActualAnswer']}"

#         # Run the evaluation
#         try:
#             result = graph.invoke({"question_answer": qa_pair, "result": {}})

#             # Extract the results
#             evaluation = result["result"]

#             # Update the row with evaluation results
#             df.at[index, "Similar"] = evaluation.get("similar", "N/A")
#             df.at[index, "Score"] = evaluation.get("score", 0)
#             df.at[index, "Reason"] = evaluation.get("reason", "")

#             # Print progress
#             print(f"Processed row {index + 1}/{len(df)}")
#         except Exception as e:
#             print(f"Error processing row {index + 1}: {str(e)}")

#     # Save the updated dataframe to a new CSV file
#     df.to_csv(output_file, index=False)
#     print(f"Results saved to {output_file}")


# # Example usage
# if __name__ == "__main__":
#     # Instantiate the graph
#     # graph = create_qa_evaluation_graph()

#     # # Test example
#     # example_qa = "ตามที่สั่งไปสินค้าไป ไม่ประสงค์รับใบกำกับภาษีนะคะ|สวัสดีครับคุณลูกค้ามีอะไรให้ช่วยคับ"

#     # # Run the graph
#     # result = graph.invoke({
#     #     "question_answer": example_qa,
#     #     "result": {}
#     # })

#     # # Print the result
#     # print("Question-Answer pair:", example_qa)
#     # print("Evaluation result:", json.dumps(result["result"], indent=2, ensure_ascii=False))
#     process_csv_file()


# """This module provides functionality to process user text and interact with the agent graph.

# It includes a function to process text with a thread ID and display name, and a main entry point
# to demonstrate the interaction with the agent graph.
# """

# graph.checkpointer = MemorySaver()


# def check_answer_relevance(row):
#     query = row["ActualQuery"].strip()
#     answer = row["ActualAnswer"].strip()

#     if query and answer:
#         if query in answer or any(word in answer for word in query.split()):
#             return "ตรงกับคำถาม"
#         else:
#             return "ไม่ตรงกับคำถาม"
#     return "ไม่สามารถวิเคราะห์ได้"


# def process_text(text: str, thread_id: str, display_name: str):
#     """Invoke the agent graph with a user text and thread (or session) identifier."""
#     config = {"configurable": {"thread_id": thread_id, "username": display_name}}
#     result = graph.invoke({"messages": ("user", text)}, config=config)
#     return result["messages"][-1].content.replace("www.dam", "dam")


# def process_img(data_url: str, thread_id: str):
#     """Invokes the agent graph with an image and thread (or session) identifier."""
#     config = {"configurable": {"thread_id": thread_id}}
#     message_content = [
#         {
#             "type": "image_url",
#             "image_url": {
#                 "url": data_url,
#             },
#         },
#     ]
#     image_message = HumanMessage(content=message_content)
#     result = graph.invoke(
#         {"messages": [("user", "the user sent this image (This is just the system message)"), image_message]},
#         config=config,
#     )
#     return result["messages"][-1].content.replace("www.dam", "dam")


# def read_csv_data(csv_file_path):
#     """Read data from the CSV file."""
#     data = []
#     with open(csv_file_path, "r", encoding="utf-8") as file:
#         reader = csv.DictReader(file)
#         for row in reader:
#             data.append(row)
#     return data


# def write_csv_data(csv_file_path, data):
#     """Write the updated data back to the CSV file."""
#     fieldnames = data[0].keys() if data else []
#     with open(csv_file_path, "w", encoding="utf-8", newline="") as file:
#         writer = csv.DictWriter(file, fieldnames=fieldnames)
#         writer.writeheader()
#         writer.writerows(data)


# async def process_csv(csv_file_path):
#     """Process all queries in the CSV file and update with AI responses."""
#     data = read_csv_data(csv_file_path)
#     display_name = "kem"  # Default display name

#     for row in data:
#         text = row["ActualQuery"]
#         thread_id = row["Session"]

#         print("---------------------------------------------------------------")
#         print(f"HM[{row['ID']}]: {text.replace('\n', ' ')[:100]}")

#         # Skip empty queries
#         if not text:
#             continue

#         try:
#             # Check if the text starts with http (URL/image)
#             if text.lower().startswith("http"):
#                 response = process_img(text, thread_id)
#             else:
#                 response = process_text(text, thread_id, display_name)

#             row["ActualAnswer"] = response
#             print(
#                 f"AI: {response.replace('\n', ' ')[:100]} ..."
#             )  # Print first 100 chars of response with newlines replaced by spaces
#         except Exception as e:
#             row["ActualAnswer"] = e
#             print(f"AI: Error {row['ID']}: {e}")

#         row["SimilarPhrase"] = check_answer_relevance(row)

#     write_csv_data("retest-result.csv", data)
#     print("CSV processing completed.")


# async def main():
#     """Define the main entry point for the asynchronous application."""
#     csv_file_path = "retest.csv"

#     # Ensure the CSV file exists
#     if not os.path.exists(csv_file_path):
#         print(f"Error: CSV file not found at {csv_file_path}")
#         return

#     await process_csv(csv_file_path)


# if __name__ == "__main__":
#     asyncio.run(main())
