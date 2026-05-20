import streamlit as st
st.title("Wahid Streamlit App")
st.write("This is a simple Streamlit app created by Wahid.")
st.write("You can add more features and functionalities to this app as needed.")    
st.write("Feel free to explore Streamlit and create amazing applications!")
st.subheader("This is a subheader")
st.write("You can also add images, charts, and other interactive elements to make your app more engaging.")
st.write("For example, you can use the `st.line_chart` function to create a line chart:")
import pandas as pd
import numpy as np
data = pd.DataFrame(np.random.randn(20, 3), columns=['A', 'B', 'C'])
st.line_chart(data)
st.write("This is just a basic example. You can customize the chart and add more features to make it more informative and visually appealing.")
st.write("Streamlit makes it easy to create interactive web applications with Python. You can use various Streamlit components to build your app, such as buttons, sliders, and text inputs.")
st.write("For example, you can use the `st.button` function to create a button:")
if st.button("Click me"):
    st.write("Button clicked!")
st.write("You can also use the `st.slider` function to create a slider:")
slider_value = st.slider("Select a value", 0, 100, 50)
st.write(f"Selected value: {slider_value}")
st.write("This is just a glimpse of what you can do with Streamlit. The possibilities                                     are endless! You can create complex applications with multiple pages, user authentication, and much more.")
st.write("To learn more about Streamlit and its features, you can check out the official documentation at https://docs.streamlit.io/")
st.write("Happy coding and have fun building your Streamlit app!")      