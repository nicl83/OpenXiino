use html_editor::{
    self,
    operation::{Editable, Htmlifiable, Selector},
    Element, Node,
};

use crate::supported_tags::SUPPORTED_TAGS;

// Parse HTML to remove tags Xiino does not support.
// TODO: EBDIMAGE conversion
pub fn parse_html(html: &str) -> String {
    let mut doc_tree = match html_editor::parse(html) {
        Ok(tree) => tree,
        Err(error) => return error_page(error),
    };
    #[cfg(debug_assertions)]
    {
        println!("RTS: ---- CUT HERE ----");
    }
    doc_tree.retain_mut(recursive_tag_stripper);
    let html = doc_tree.trim().html();
    // HACK: workaround to mystery Xiino behaviour
    format!("            {}", html)
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
    let html = err_page
        .insert_to(&Selector::from("body"), err_tag)
        .trim()
        .html();
    format!("            {html}") // Sometimes, I really hate developing for closed-source software
}

/// Check to see if a Node is supported by Xiino.
/// Designed for use with `retain_mut`.
fn recursive_tag_stripper(node: &mut Node) -> bool {
    if let Some(element) = node.as_element_mut() {
        if SUPPORTED_TAGS.contains(&element.name.to_lowercase().as_str()) {
            // debug hackery ahead, strip for release
            #[cfg(debug_assertions)]
            {
                println!("RTS: kept tag {}", element.name);
            }
            if element.children.len() > 0 {
                element.children.retain_mut(recursive_tag_stripper);
            }
            true
        } else {
            #[cfg(debug_assertions)]
            {
                println!("RTS: dropped tag {}", element.name);
            }
            false
        }
    } else {
        return true;
    }
}

/// Replace HTML special chars with their escaped equivelants.
/// Used for debugging.
pub fn escape_error_data(error: String) -> String {
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

    #[test]
    fn recursive_tag_stripper_testpilot() {
        let html = r#"
            <!DOCTYPE HTML>
            <html>
                <head>
                    <title>Example</title>
                </head>
                <body>
                    <p>This tag should be kept.</p>
                    <foobar>This tag should not be kept.</foobar>
                </body>
            </html>
        "#;
        println!("{}", parse_html(html));
    }
}
