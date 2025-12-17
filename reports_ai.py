import openai

openai.api_key = "YOUR_API_KEY"

def generate_report(df, report_type):
    summary = df.describe().to_string()

    prompt = f"""
You are a business analyst.

Generate a {report_type} report based on this dataset summary:
{summary}

Include:
- Executive summary
- Key insights
- Trends
- Actionable recommendations
"""

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.6
    )

    return response.choices[0].message.content
