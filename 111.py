import streamlit as st
import streamlit.components.v1 as components

html = """
<!DOCTYPE html>
<html>
<head>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/p5.js/1.4.1/p5.js"></script>
</head>
<body>
<script>
function setup() {
  createCanvas(200, 200);
  background(200);
}
function draw() {
  ellipse(mouseX, mouseY, 20, 20);
}
</script>
</body>
</html>
"""

st.title("p5 test")
components.html(html, height=250)
