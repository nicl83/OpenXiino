pub mod html_parse;
pub mod supported_tags;

use std::net::SocketAddr;
use std::{error, fmt};

use axum::{
    extract::{Path, RawQuery},
    http::{self, request, HeaderMap, Response, StatusCode, Uri},
    response::{Html, IntoResponse},
    routing::get,
    Router,
};
use html_editor::parse;
use html_parse::parse_html;
use reqwest::Request;
use serde::Deserialize;

use crate::html_parse::escape_error_data;

#[tokio::main]
async fn main() {
    // std::env::set_var("RUST_LOG", "trace"); // NEVER do this
    tracing_subscriber::fmt::init();
    // build our application with a route
    let app = Router::new()
        .route("/:depth/:width/:unknown/:encoding/", get(handler))
        .fallback(fallback_handler);

    // run it
    let addr = SocketAddr::from(([127, 0, 0, 1], 8000));
    println!("listening on {}", addr);
    axum::Server::bind(&addr)
        .serve(app.into_make_service())
        .await
        .unwrap();
}

#[axum_macros::debug_handler]
async fn handler(
    Path((colour_depth, screen_width, _, text_encoding)): Path<(String, String, String, String)>,
    RawQuery(url): RawQuery,
    headers: HeaderMap,
) -> impl IntoResponse {
    let uri: Uri = url
        .unwrap_or("http://invalid_url".to_string())
        .parse()
        .unwrap();

    let device_info = DeviceInfo::new(colour_depth, screen_width, text_encoding);

    let resp: Result<_, _> = match uri.host().unwrap() {
        "deviceinfo" => show_device_info(device_info, uri).await,
        _ => do_proxy(device_info, uri).await,
    };

    resp.map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)
}

async fn fallback_handler() -> Html<String> {
    Html(
        "
    <html>
    <h1>Strange request!</h1>
    <p>Your version of Xiino is making requests in a way OpenXiino can't handle.</p>
    <p>Make sure you're using the latest version of Xiino, then try again.</p>
    </html>
    "
        .to_string(),
    )
}

async fn show_device_info(
    device_info: DeviceInfo,
    uri: Uri,
) -> Result<Response<String>, http::Error> {
    let width = device_info.screen_width;
    let mode = device_info.screen_mode;
    let depth = device_info.screen_depth;
    let encoding = device_info.text_encoding;
    let html = format!(
        "
        <html>
        <body>
        <ul>
        <li>Device width: {width}px</li>
        <li>Colour mode: {mode}</li>
        <li>Colour depth: {depth}</li>
        <li>Text encoding: {encoding}</li>
        <li>Requested URL: {uri}</li>
        </ul>
        </body>
        </html>
        "
    );
    Response::builder()
        .header("Content-Type", "text/html")
        .body(html)
}

async fn do_proxy(device_info: DeviceInfo, url: Uri) -> Result<Response<String>, http::Error> {
    #[cfg(debug_assertions)]
    {
        println!("doing a proxy request for {url}...")
    }
    let client = reqwest::Client::builder()
        .user_agent("OpenXiino/1.0 (http://github.com/nicl83/openxiino) / reqwest 0.11.20")
        .build()
        .unwrap();
    let http_get_result = match client.get(url.to_string()).send().await {
        Ok(result) => result,
        Err(e) => return Ok(error_page(e.to_string())), // it's not ok but shh
    };
    dbg!(http_get_result.headers());
    let html = match http_get_result.text().await {
        Ok(html) => html,
        Err(e) => return Ok(error_page(e.to_string())),
    };

    let parsed_html = dbg!(parse_html(&html));
    #[cfg(debug_assertions)]
    {
        println!("proxy request done")
    }
    Response::builder()
        .header("Content-Type", "text/html")
        .body(parsed_html)
}

fn error_page(error: String) -> Response<String> {
    let clean_error = escape_error_data(error);
    Response::builder()
        .header("Content-Type", "text/html")
        .body(format!(
            r#"
        <!DOCTYPE HTML>
        <html>
        <body>
        <h1>Proxy failure!</h1>
        <p>Something went wrong while making a proxy request.<p>
        <code>{clean_error}</code>
        </html>
        </body>
        "#
        ))
        .unwrap()
}

enum ScreenType {
    Grayscale,
    Colour,
}

impl fmt::Display for ScreenType {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match *self {
            ScreenType::Colour => write!(f, "Colour"),
            ScreenType::Grayscale => write!(f, "Grayscale/Monochrome"),
        }
    }
}

struct DeviceInfo {
    screen_width: u32,
    screen_mode: ScreenType,
    screen_depth: u32,
    text_encoding: String,
}

impl DeviceInfo {
    fn new(colour_depth: String, screen_width: String, text_encoding: String) -> Self {
        let width: u32 = screen_width[1..].parse().unwrap_or(153); // safe fallback
        let mode: ScreenType = match &colour_depth[..1] {
            "g" => ScreenType::Grayscale,
            "c" => ScreenType::Colour,
            _ => ScreenType::Grayscale, // fallback
        };
        let depth = match colour_depth[1..].parse::<u32>() {
            Ok(depth) => depth,
            Err(_) => {
                // if colour, return 16 (only value I've ever seen)
                // if grayscale, return 4 (16-shade grey, should parse fine on other monochrome types)
                match mode {
                    ScreenType::Colour => 16,
                    ScreenType::Grayscale => 4,
                }
            }
        };
        let encoding = text_encoding[1..].to_string(); // discard leading "e" character
        Self {
            screen_width: width,
            screen_mode: mode,
            screen_depth: depth,
            text_encoding: encoding,
        }
    }
}
