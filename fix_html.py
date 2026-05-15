import io

with open('core/templates/message.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Fix the escaped backticks and dollar signs
text = text.replace('\\`', '`')
text = text.replace('\\$', '$')

# Fix the broken renderMessages declaration
bad_decl = "if(inp && activeEditId) inp    function renderMessages(msgs, other) {"
good_decl = "if(inp && activeEditId) inp.value = '';\n    }\n\n    function renderMessages(msgs, other) {"
text = text.replace(bad_decl, good_decl)

with open('core/templates/message.html', 'w', encoding='utf-8') as f:
    f.write(text)
