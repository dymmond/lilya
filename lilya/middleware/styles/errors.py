def get_css_style() -> str:
    """
    Returns the CSS for the template.
    """
    style = """
    <style type='text/css'>
        p {
            color: #211c1c;
        }
        .container {
            border: 1px solid #B33A3A;
        }
        .margin-top-none {
            margin-top: 0;
        }
        .title {
            background-color: #B33A3A;
            color: lemonchiffon;
            padding: 12px;
            font-size: 22px;
            font-weight: bolder;
        }
        .frame-line {
            padding-left: 10px;
            font-family: monospace;
        }
        .frame-filename {
            font-family: monospace;
        }
        .center-line {
            background-color: #B33A3A;
            color: #f9f6e1;
            padding: 5px 0px 5px 5px;
        }
        .lineno {
            margin-right: 5px;
        }
        .frame-container {
            background-color: #f9f6f6;
        }
        .frame-title {
            font-weight: unset;
            padding: 10px 10px 10px 10px;
            background-color: #ffe4e4;
            color: #191f21;
            font-size: 17px;
            border: 1px solid #c7dce8;
        }
        .collapse-btn {
            float: right;
            padding: 0px 5px 1px 5px;
            border: solid 1px #96aebb;
            cursor: pointer;
        }
        .collapsed {
            display: none;
        }
        .source-code {
            font-family: courier;
            font-size: small;
            padding-bottom: 10px;
        }

    </style>
    """
    return style


def get_js() -> str:
    js = """
    <script type="text/javascript">
        function collapse(element){
            const frameId = element.getAttribute("data-frame-id");
            const frame = document.getElementById(frameId);

            if (frame.classList.contains("collapsed")){
                element.innerHTML = "&#8210;";
                frame.classList.remove("collapsed");
            } else {
                element.innerHTML = "+";
                frame.classList.add("collapsed");
            }
        }
    </script>
    """
    return js


def get_frame() -> str:
    frame = """
    <div class="frame-container">
    <p class="frame-title">File <span class="frame-filename">{frame_filename}</span>,
        line <i>{frame_lineno}</i>,
        in <b>{frame_name}</b>
        <span class="collapse-btn" data-frame-id="{frame_filename}-{frame_lineno}" onclick="collapse(this)">{collapse_button}</span>
        </p>
        <div id="{frame_filename}-{frame_lineno}" class="source-code {collapsed}">{code_context}</div>
    </div>
    """
    return frame


def get_line() -> str:
    line = """
    <p><span class="frame-line">
    <span class="lineno">{lineno}.</span> {line}</span></p>
    """
    return line


def get_center_line() -> str:
    line = """
    <p class="center-line"><span class="frame-line center-line">
    <span class="lineno">{lineno}.</span> {line}</span></p>
    """
    return line


def get_template_errors() -> str:
    """
    Returns the HTML for the server errors being
    displayed.
    """
    html = """
    <html>
        <head>
            <style type='text/css'>
                {styles}
            </style>
            <title>Lilya Debugger</title>
        </head>
        <body>
            <h1>HTTP 500 Server Error</h1>
            <h2>{error}</h2>
            <div class="container">
                <p class="title margin-top-none">Traceback</p>
                <div>{exc_html}</div>
            </div>
            {js}
        </body>
    </html>
    """
    return html
