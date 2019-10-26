### check-sg.py

# Explanation 
This is a lambda triggered by AWS config. It will check if security groups that have 0.0.0.0/0 or ::/0 within ports "0, 22, 23, 125, 1433, 1434, 1521, 3306, 3389, 5432" are only open to Matson subnet unless they are part of the excluded list