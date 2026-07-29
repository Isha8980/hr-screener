from app.resume_parser import parse_resume

text = """
Summary
A part-qualified actuary with a passion for data science and nearly three years of experience in the general insurance industry. Confident and
capable of playing a key role in a leading consultancy firm or insurance and financial services company. An innovative and highly focused individual with a deep interest in analytical work and data interpretation. Would like to work in an organisation that promotes both individual and
organisational growth.
Experience
Marsh McLennan Mumbai, India
Actuarial Analyst Nov 2020 - Sept 2022
- Built risk models considering client's risk by combining client's historical loss experience (includes building a stochastic model to calculate the
expected loss costs) and Marsh's proprietary risk exposure-based model.
- Developed a Monte Carlo simulations-based trade credit risk model in both R and Python. The model takes buyers' Probability of Default, Loss
Given Default and Exposure at Default into account and generates results for both gross (ground-up) and net (insured) losses.
- Facilitated the development of the property damage and business interruption risk model that runs simulations in VBA based on the Swiss Re
curves, the total insured value of properties and empirical losses of the client.
- Facilitated the development of the cyber risk model by transforming the output into a clear and easy-to-understand format.
- Determined the best estimates of the loss reserves and ultimate liability and calculated a range around the best estimates to quantify the
uncertainty.
- Identified the most optimal (i.e., financially efficient blend of premium and retained loss cost, including associated volatility) insurance structure
within the client's appetite for risk.
- Planned, managed and delivered projects efficiently on schedule as a project manager.
- Provided training on pricing and reserving processes to new joiners, which involved delivering detailed instructions and answering queries.
- Technical Skills: Python, R, MS Excel and Advanced Excel, VBA, MS PowerPoint, MS Word, MetaRisk (Proprietary Software).
- Soft Skills: Teamwork, Time Management, Communication, Presentation skills, Report Writing, Leadership, Analytical Thinking.
Milliman Gurugram, India
Actuarial Intern Jan 2020 - Nov 2020
- Developed a Generalised Linear Model-based tool using R, SAS, and VBA to automate the insurance pricing process, increasing the processing
speed by nearly ten times while standardising the process.
- Collected and analysed data of all the general insurance companies of India in specifically designed and standardised Excel templates.
- Analysed and reviewed property and casualty insurance policy content based on policy documents and checklists provided by insurance companies, maintenance organisations and related entities.
- Technical Skills: SAS, R, MS Excel and Advanced Excel, VBA.
- Soft Skills: Time Management, Communication, Analytical Thinking.
EY Gurugram, India
Data Analytics Intern
- Collected and processed large sets of data from various sources.
- Performed basic data manipulation and statistical analysis on the data using Alteryx.
- Technical Skills: Alteryx, SQL, MS Excel.
- Soft Skills: Time Management, Communication, Analytical Thinking.
Nov 2019 - Jan 2020
Education
University of Leeds Leeds, UK
MSc in Data Science and Analytics Sept 2022 - Sept 2023
- Relevant Coursework: Data Science, Machine Learning, Deep Learning, Statistical Learning, Statistical Computing
Institute and Faculty of Actuaries, UK
Professional Qualification - Actuarial Exams
Sept 2016 - Present
University of Delhi B.A. (Honours) in Economics New Delhi, India
July 2016 - July 2019
- Minor in Mathematics
- Relevant Coursework: Data Analysis, Elements of Analysis, Statistical Methods for Economics, Mathematical Methods for Economics, Econometrics, Financial Economics.
Projects
Image Classification using Neural Networks
- Technical Skills: Python.
Customer Personality Analysis
- Conducted a customer personality analysis on Python using K-Means clustering.
- Technical Skills: Python, Tableau, Overleaf (LaTex).
"""

candidate = parse_resume(text)
print("Extracted skills:")
for s in candidate.skills:
    print(" -", s)
print()
print("Experience years:", candidate.experience_years)
print("Education:", candidate.education)