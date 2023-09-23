use html_editor::{
    self,
    operation::{Editable, Htmlifiable, Selector},
    Node,
};

// Parse HTML to remove tags Xiino does not support.
pub fn parse_html(html: &str) -> String {
    let doc_tree = match html_editor::parse(html) {
        Ok(tree) => tree,
        Err(error) => return error_page(error),
    };
    "foobar".to_string()
}

fn error_page(error: String) -> String {
    let mut err_page = html_editor::parse(
        r#"
        <!DOCTYPE HTML>
        <html>
            <head>
            <title>HTML Parse Error</title>
            </head>
            <body>
            <h1>The following error was encountered while parsing HTML:</h1>
            </body>
        "#,
    )
    .unwrap();
    let err_tag = Node::new_element("p", vec![], vec![Node::Text(error)]);
    err_page
        .insert_to(&Selector::from("body"), err_tag)
        .trim()
        .html()
}
