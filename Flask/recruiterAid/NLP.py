from pyresparser import ResumeParser
data = ResumeParser('sampo.pdf').get_extracted_data()
# data = ResumeParser('C:/Users/Dell/Desktop/Projects/FinalYearProject/Git/Flask/recruiterAid/static/ResumeFiles/
#                     sampd.pdf', skills_file='C:/Users/Dell/Desktop/Projects/FinalYearProject/Git/Flask/recruiterAid/'
#                                              'static/skills.csv').get_extracted_data()

print('\n')
print('Name: ', data['name'])
print('Email: ', data['email'])
print('Contact Number: ', data['mobile_number'])
print('College Name: ', data['college_name'])
print('Degree: ', data['degree'])
print('Skills: ', data['skills'])
print('Company Name: ', data['company_names'])
print('Designation: ', data['designation'])
print('Total Experience: ', data['total_experience'])
print('Total number of Resume pages: ', data['no_of_pages'])
