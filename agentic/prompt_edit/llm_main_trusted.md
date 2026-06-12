
<!--
Instruction : The following instructions, written in Markdown format, must be strictly followed.
-->
# Message Classification Guidelines
Since categories are sorted by importance, select the one that best matches the message's intent.

Categories:
- `tool_calls` A response that indicates the system is actively calling or using an internal tool or function (e.g., search, recommendation engine) without asking the customer any follow-up questions or expecting user input.
- `assistance` A response that expresses readiness to assist by prompting or asking for more details, or offering help without performing an immediate system/tool action.
- `follow_up`  response indicating that the system is asking the user for additional details or clarification in order to proceed or provide a more accurate answer.
- `confirm_option` A response that prompts the user to confirm a question or request assistance from an operator.
- `contact_operator`  A response that prompts the user to request assistance from an operator or informs them that their request will be forwarded to one.
- `option_pickup` A response that shows a list of predefined options and asks the user to pick one — helping guide them to a specific answer, such as a list of products.
- `general` This response that don’t fit into any of the above categories. This is a general category for normal conversation, questions, or responses unrelated to searching or barcodes.

# situation Guidelines
A concise and well-written summary of the user's situation or request for assistance, presented in Thai.
