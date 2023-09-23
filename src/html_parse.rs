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
        </html>
        "#,
    )
    .unwrap();
    let err_tag = Node::new_element("code", vec![], vec![Node::Text(escape_error_data(error))]);
    err_page
        .insert_to(&Selector::from("body"), err_tag)
        .trim()
        .html()
}

fn escape_error_data(error: String) -> String {
    error
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn invalid_html() {
        const INVALID_HTML: &str = r#"
        <!DOCTYPE html> 
        <html lang="en">
        <head> 
        <meta charset="UTF-8" />
        <title>Invalid HTML Example</title>
        </head> 
        <body>
        <h1>Invalid HTML Example</h1>
        <p>On this page, we will do some things wrong, so we can see the validator catch them.</p>

        <p>On the web, we can create links to pages like, the <a href="http://www.w3.org/"><abbr title="World Wide Web Consortium">W3C</a>, the group that defines web technologies like HTML.</p>

        <p>An <a href="http://validator.w3.org/>HTML Validator</a> is a tool that helps us find errors. Oops, that was another mistake.</p>


        </body>
        </html>
        "#; // credit to https://www2.cs.sfu.ca/CourseCentral/165/common/study-guide/files/invalid.html
        let result = parse_html(INVALID_HTML);
        dbg!(&result);
        assert!(result.contains("HTML Parse Error"));
    }
}
