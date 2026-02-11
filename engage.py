import requests
import re
import json
import os
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

version = "1.4"

print("Engage CLI Version " + version)
print("By Sea :)")
print("\n")



def load_config(config_path='engage.config'):
    accounts = []
    current_acc = {}
    subdomain = None
    special = None
    
    if not os.path.exists(config_path):
        print(f"Error: Configuration file '{config_path}' not found.")
        exit(1)

    with open(config_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith('subdomain:'):
                 _, val = line.split(':', 1)
                 subdomain = val.strip()
                 continue
            
            if line.startswith('acc'):
                if current_acc:
                    accounts.append(current_acc)
                current_acc = {}
            elif ':' in line:
                key, value = line.split(':', 1)
                current_acc[key.strip()] = value.strip()
                
        if current_acc:
            accounts.append(current_acc)
            
    return accounts, subdomain

accounts, subdomain = load_config()


def getscores():
    get_scores_url = f'{base_url}/Services/PupilAssessmentServices.asmx/GetReportingAssessmentReportingPeriods'
    print("Getting your scores...")
    
    headers = {
        'Content-Type': 'application/json; charset=UTF-8',
        'Origin': base_url
    }
    
    data = {
        "encryptedPupilID": pid
    }
    
    
    scores_response = session.post(get_scores_url, headers=headers, json=data)
    try:
        # The response 'd' contains a stringified JSON list
        response_data = scores_response.json()
        if 'd' in response_data:
            reporting_periods = json.loads(response_data['d'])
        else:
            reporting_periods = response_data

        print("\nSelect a Reporting Period:")
        for i, period in enumerate(reporting_periods):
            print(f"{i+1}. [{period['AcademicYearText']}] {period['Name']}")
        
        selection = int(input("\nEnter your choice: ")) - 1
        
        if 0 <= selection < len(reporting_periods):
            selected_period = reporting_periods[selection]
            
            # Fetch the actual scores for the selected period
            print(f"Fetching scores for {selected_period['Name']}...")
            
            score_data = {
                "encryptedPupilID": pid,
                "academicYear": str(selected_period['AcademicYear']),
                "reportingPeriodId": str(selected_period['ReportingPeriodId']),
                "subjectIds": "",
                "sectionType": "PupilAssessments"
            }
            
            assessment_url = f'{base_url}/Services/PupilAssessmentServices.asmx/RenderSimpleSection'
            assessment_response = session.post(assessment_url, headers=headers, json=score_data)
            
            print(f"Assessment Response Code: {assessment_response.status_code}")
            
            try:
                # The response 'd' is the HTML content
                assessment_json = assessment_response.json()
                html_content = assessment_json.get('d', '')
                
                # Split content by class/subject
                # Pattern: class="pupilAssessmentContent paddingBottom10">\r\n\t\t\t<h1>
                # We can split by the class attribute to get chunks
                class_blocks = re.split(r'class="pupilAssessmentContent paddingBottom10">\s*<h1>', html_content)
                
                subjects = []
                # Skip the first block as it's likely header/preamble before the first class
                for block in class_blocks[1:]:
                    # The first part of the block until </h1> is the class name
                    # Using partition to separate name from rest
                    name_part, sep, rest = block.partition('</h1>')
                    if sep:
                        subjects.append({
                            'name': name_part.strip(),
                            'content': rest
                        })

                if not subjects:
                    print("No subjects found.")
                    # Fallback to printing raw if parsing fails
                    # print(f"Assessment Content (Raw): {html_content}") 
                    return selected_period

                print("\nSelect a Subject:")
                for i, subject in enumerate(subjects):
                    print(f"{i+1}. {subject['name']}")
                
                # Special PDF option for parents
                if is_parent and ENABLE_PDF_GEN:
                    print("g. Generate pdf")
                
                choice_str = input("\nEnter your choice: ").strip().lower()
                
                if choice_str == 'g' and is_parent and ENABLE_PDF_GEN:
                    import extras
                    print("Generating PDF Report...")
                    
                    # We need to extract scores for ALL subjects
                    # Based on existing logic for single subject, we need to generalize it.
                    score_matrix = []
                    
                    for subj in subjects:
                         # Heuristic: Find first numeric score or "idk..."
                         # Similar regex to single subject view
                         labels = re.findall(r'class="pupilAssessmentLabel">(.*?)<', subj['content'])
                         scores = re.findall(r'class="pupilAssessmentRO right">(.*?)<', subj['content'])
                         
                         # Just get the last score for now as a representative score, or try to find a "Total" or "Grade"
                         if scores:
                             # Clean scores
                             cleaned_scores = [s.replace('&nbsp;', ' ').strip() for s in scores]
                             # Find the first one that looks like a number, or take the last one
                             final_score = "idk, you tell me"
                             
                             # Prioritize non-empty
                             valid_scores = [s for s in cleaned_scores if s and any(c.isdigit() for c in s)]
                             if valid_scores:
                                 final_score = valid_scores[-1] # Take the last valid score usually
                             
                             score_matrix.append([subj['name'], "idk, you tell me", final_score])
                         else:
                             score_matrix.append([subj['name'], "idk, you tell me", "idk, you tell me"])
                    
                    extras.generate_report(score_matrix)
                    print("PDF Generated! Check report.pdf")
                    # Wait for user
                    input("Press Enter to continue...")
                    return selected_period

                if choice_str.isdigit():
                    subject_selection = int(choice_str) - 1
                else:
                    subject_selection = -1
                
                if 0 <= subject_selection < len(subjects):
                    selected_subject = subjects[subject_selection]
                    print(f"\n--- {selected_subject['name']} ---")
                    
                    # Parse rows in the selected subject
                    # Each row has a Label and a Score (RO right)
                    # We can regex for pairs orfindall individually.
                    # Given the structure, finding all labels and scores in order might work if they align.
                    # Work Name: class="pupilAssessmentLabel">(.*?)</div> (or <)
                    # Score: class="pupilAssessmentRO right">(.*?)</div>
                     
                    # Let's find matches. We assume they appear in pairs.
                    # Using a combined regex or iterating through the block line by line might be safer if structure varies.
                    # But let's try findall for both separately and zip them, or find chunks.
                    
                    # Let's look for rows. Usually wrapped in something? 
                    # If we just grep all labels and all scores, hopefully they match 1:1.
                    
                    labels = re.findall(r'class="pupilAssessmentLabel">(.*?)<', selected_subject['content'])
                    scores = re.findall(r'class="pupilAssessmentRO right">(.*?)<', selected_subject['content'])
                    
                    # Check if lengths match
                    count = min(len(labels), len(scores))
                    for k in range(count):
                        label_clean = labels[k].strip()
                        score_clean = scores[k].strip()
                        # Removing HTML entities if any (simple replace for now)
                        label_clean = label_clean.replace('&amp;', '&').replace('&nbsp;', ' ')
                        score_clean = score_clean.replace('&nbsp;', ' ')
                        
                        print(f"{label_clean}: {score_clean}")
                        
                else:
                    print("Invalid subject selection.")

            except json.JSONDecodeError:
                print(f"Assessment Content (Raw): {assessment_response.text}")


            return selected_period
        else:

            print("Invalid selection.")
            return None

    except json.JSONDecodeError:
         # Fallback to text if not valid JSON
        print(f"Scores Content (Raw): {scores_response.text}")
        return None

def getdetails():
    details_url = f'{base_url}/Services/PupilDetailsServices.asmx/RenderSimpleSection'
    print("Getting your details...")
    
    headers = {
        'Content-Type': 'application/json; charset=UTF-8',
        'Origin': base_url
    }
    
    data = {
        "encryptedPupilID": pid,
        "sectionType": "PupilDetails"
    }
    
    response = session.post(details_url, headers=headers, json=data)
    
    try:
        response_json = response.json()
        html_content = response_json.get('d', '')
        
        # Regex to find key-value pairs (Pupil Format)
        matches = re.findall(r'<th.*?>(.*?)</th>\s*<td.*?>(.*?)</td>', html_content, re.DOTALL)
        
        cleaned_matches = []
        for key, value in matches:
            # Clean up keys and values
            key = re.sub(r'<[^>]+>', '', key).strip()
            value = re.sub(r'<[^>]+>', '', value).strip()
            # Replace common entities
            key = key.replace('&amp;', '&').replace('&nbsp;', ' ')
            value = value.replace('&amp;', '&').replace('&nbsp;', ' ')
            cleaned_matches.append((key, value))
            
        if cleaned_matches:
             # Based on observation, the order seems to be [Right1, Left1, Right2, Left2...]
            # So Index 1, 3... are Left Field (First Name, etc)
            # Index 0, 2... are Right Field (Entry Date, etc)
            
            left_col = cleaned_matches[1::2]
            right_col = cleaned_matches[0::2]
            
            # Combine and formatting
            all_details = left_col + right_col
            
            # Keys to exclude
            exclude_keys = ['Home Tutor', 'Additional Tutors']
            
            print("\n--- Personal Details (Pupil) ---")
            counter = 1
            for key, value in all_details:
                 # Strict clean
                 key = ' '.join(key.split())
                 value = ' '.join(value.split())
                 
                 # Filter logic
                 if "Tutor" in key or "Student Affairs" in key:
                     continue
                     
                 if key and value and key not in exclude_keys:
                     print(f"{counter}. {key}: {value}")
                     counter += 1
            return

    except (json.JSONDecodeError, ValueError):
        # Fallthrough to Parent logic
        pass

    # Fallback: Parent Account / MyDetails.aspx
    # If the JSON/HTML parsing above failed or returned nothing
    print("Trying parent details scraping...")
    details_page_url = f'{base_url}/MyDetails.aspx'
    
    details_resp = session.get(details_page_url)
    if details_resp.status_code != 200:
        print(f"Failed to load details page. Code: {details_resp.status_code}")
        return

    soup = BeautifulSoup(details_resp.text, 'html.parser')
    my_details_div = soup.find('div', id='myDetails')
    
    if not my_details_div:
        print("No details found (myDetails div missing).")
        return

    columns = my_details_div.find_all('div', class_='column')
    
    if not columns:
        print("No detail columns found.")
        return

    print("\n--- Personal Details (Parent) ---")
    
    for i, col in enumerate(columns):
        # Extract text from the column, preserving structure roughly
        # Usually it's Label: Value or just lines
        text = col.get_text(separator='\n', strip=True)
        lines = text.split('\n')
        
        # Display as a section
        print(f"\n[Section {i+1}]")
        for line in lines:
            line = line.strip()
            if line:
                 print(f"  {line}")

def getassessment():
    assessment_url = f'{base_url}/Services/PupilDetailsServices.asmx/GetPupilAssessmentReports'
    print("Getting your assessment reports...")
    
    headers = {
        'Content-Type': 'application/json; charset=UTF-8',
        'Origin': base_url
    }
    
    data = {
        "encryptedPupilID": pid,
        "reportingPeriod": "",
        "academicYear": 0,
        "showAllReports": True
    }
    
    response = session.post(assessment_url, headers=headers, json=data)
    
    try:
        response_data = response.json()
        if 'd' in response_data:
            reports = json.loads(response_data['d']) if isinstance(response_data['d'], str) else response_data['d']
        else:
            reports = response_data
            
        # Handle case where 'd' might be directly the list or nested
        # Based on previous patterns, it might be a list directly or inside 'd'
        # The user said "extract the AcademicYearText and Title", implying a list of objects.
        
        if not reports:
            print("No assessment reports found.")
            return

        print("\nSelect an Assessment Report:")
        for i, report in enumerate(reports):
            # Using .get to be safe, though user specified keys
            year_text = report.get('AcademicYearText', 'N/A')
            title = report.get('Title', 'No Title')
            print(f"{i+1}. [{year_text}] {title}")
            
        selection = int(input("\nEnter your choice: ")) - 1
        
        if 0 <= selection < len(reports):
            selected_report = reports[selection]
            uri = selected_report.get('Uri', '')
            if uri:
                full_link = f"{base_url}{uri}"
                print(f"\nLink: {full_link}")
            else:
                print("\nError: No URI found for this report.")
        else:
            print("Invalid selection.")

    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error parsing response: {e}")



def getschedule():
    schedule_url = f'{base_url}/VLE/WeeklyTimetable.aspx'
    print("Getting your weekly schedule...")
    
    # Week Selection
    print("\nSelect week:")
    print("0. This Week")
    for i in range(1, 6):
        print(f"{i}. +{i} Week(s)")
    
    try:
        week_offset = int(input("Enter choice (0-5): "))
        if not (0 <= week_offset <= 5):
            print("Invalid selection. Defaulting to This Week.")
            week_offset = 0
    except ValueError:
         print("Invalid input. Defaulting to This Week.")
         week_offset = 0

    response = session.get(schedule_url, headers={'Origin': base_url})
    
    if response.status_code != 200:
        print(f"Failed to fetch schedule page. Status Code: {response.status_code}")
        return

    # If offset is 0, we can use the GET response directly.
    # If offset > 0, we need to POST to change the date.
    
    if week_offset > 0:
        print(f"Fetching schedule for +{week_offset} weeks...")
        
        # We need to simulate clicking "Next Week" button week_offset times.
        # This is safer than trying to manipulate the intricate Telerik DatePicker state manually.
        
        current_soup = BeautifulSoup(response.text, 'html.parser')
        
        for i in range(week_offset):
            print(f"  Jump to week +{i+1}...")
            
            # Extract ALL form inputs
            form_data = {}
        # Extract ALL form inputs
        form_data = {}
        for input_tag in current_soup.find_all('input'):
            if input_tag.get('name'):
                form_data[input_tag['name']] = input_tag.get('value', '')
        
        # Calculate Dates
        current_date = datetime.now()
        target_date = current_date + timedelta(weeks=week_offset)
        
        target_date_str = target_date.strftime('%Y-%m-%d') # 2025-12-30
        target_date_display = target_date.strftime('%d/%m/%Y') # 30/12/2025
        
        # Telerik DatePicker ClientState Construction
        # The server validates the date against this JSON state.
        client_state_value = {
            "enabled": True,
            "emptyMessage": "",
            "validationText": f"{target_date_str}-00-00-00",
            "valueAsString": f"{target_date_str}-00-00-00",
            "minDateStr": "1980-01-01-00-00-00",
            "maxDateStr": "2099-12-31-00-00-00",
            "lastSetTextBoxValue": target_date_display
        }
        client_state_json = json.dumps(client_state_value)

        # Update/Add specific fields for the schedule update
        # Force Synchronous Postback by NOT sending ScriptManager async params
        form_data.update({
            '__EVENTTARGET': 'ctl00$PageContent$weeklyTimetable$btnTimetableUpdate',
            '__EVENTARGUMENT': '',
            'ctl00$hdnUnsavedDataWarningEnabled': 'false',
            'ctl00$PageContent$weeklyTimetable$wsTimetableDate$dpWeekSelectorStartDate$dtPicker': target_date_str,
            'ctl00$PageContent$weeklyTimetable$wsTimetableDate$dpWeekSelectorStartDate$dtPicker$dateInput': target_date_display,
            'ctl00_PageContent_weeklyTimetable_wsTimetableDate_dpWeekSelectorStartDate_dtPicker_dateInput_ClientState': client_state_json
        })
        
        # Remove ScriptManager param if present to avoid Async Postback
        keys_to_remove = [k for k in form_data.keys() if 'ScriptManager' in k]
        for k in keys_to_remove:
            del form_data[k]
        
        # Re-request with POST
        response = session.post(schedule_url, data=form_data, headers={'Origin': base_url})
        
        if response.status_code != 200:
             print(f"Failed to fetch future schedule. Status Code: {response.status_code}")
             return

    # Parse (Common for both GET and POST content)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find the specific timetable table - using string ID
    table_id = "tblTimeTable_ctl00_PageContent_weeklyTimetable"
    schedule_table = soup.find('table', id=table_id)
    
    if not schedule_table:
        print("Could not find the schedule table.")
        return

    rows = schedule_table.find_all('tr')
    
    schedule_data = {}
    current_day = None
    
    for row in rows:
        # Check for Day of Week header
        day_header = row.find('th', class_='dow')
        if day_header:
            day_text = day_header.get_text(strip=True)
            # Sometimes it has 'rotate90' span, get_text handles it
            current_day = day_text
            schedule_data[current_day] = []
        
        if current_day:
            # Find all schedule cards in this row
            cards = row.find_all('td', class_='ttCard')
            for card in cards:
                # Extract details from the internal link/span
                lesson_text_span = card.find('span', class_='ttLessonText')
                if lesson_text_span:
                    # The text is separated by <br>, get_text with separator works nicely
                    # Structure usually: Subject | Time | Room | Teacher
                    full_text = lesson_text_span.get_text(separator='|', strip=True)
                    parts = [p.strip() for p in full_text.split('|')]
                    
                    # Heuristic parsing based on observed structure:
                    # Part 0: Subject
                    # Part 1: Time
                    # Part 2: Room
                    # Part 3: Teacher
                    
                    if len(parts) >= 2:
                        item = {
                            'subject': parts[0],
                            'time': parts[1],
                            'room': parts[2] if len(parts) > 2 else "N/A",
                            'teacher': parts[3] if len(parts) > 3 else "N/A"
                        }
                        schedule_data[current_day].append(item)

    # Display
    if not schedule_data:
        print("No schedule items found.")
        return

    for day, items in schedule_data.items():
        if items:
            print(f"\n=== {day.upper()} ===")
            for item in items:
                print(f"  {item['time']} : {item['subject']}")
                print(f"    Room: {item['room']} | Teacher: {item['teacher']}")

def getinbox():
    # Service Endpoints
    get_messages_url = f'{base_url}/Services/PupilMailService.asmx/GetPupilInbox'
    # User confirmed Viewing and Marking Read use GetNoticeDetail
    message_action_url = f'{base_url}/Services/PupilMailService.asmx/GetNoticeDetail'

    print("Getting your inbox...")
    
    headers = {
        'Content-Type': 'application/json; charset=UTF-8',
        'Origin': base_url
    }
    
    page = 0
    page_size = 10
    
    while True:
        print(f"\n--- Inbox (Page {page + 1}) ---")
        
        # 1. Fetch Messages
        data = {
            "pagesize": page_size,
            "page": page,
            "sort": "D",
            "search": ""
        }
        
        try:
            response = session.post(get_messages_url, headers=headers, json=data)
            
            if response.status_code != 200:
                print(f"Error fetching inbox. Status Code: {response.status_code}")
                # print(response.text) # Debug
                return

            response_json = response.json()
            # The user provided 'd' is a JSON string containing HTML
            result_html = response_json.get('d', '')
            
            # Parse the inner HTML
            soup = BeautifulSoup(result_html, 'html.parser')
            message_items = soup.find_all('div', class_='message-item')
            
            messages = []
            
            if not message_items:
                print("No messages found.")
                if page > 0:
                    print("End of list. Going back to previous page.")
                    page -= 1
                    continue
                else:
                    return

            # Display Messages
            for i, item in enumerate(message_items):
                # Extract details from HTML structure
                # Subject: span.summary > span.text (NOT .sentby)
                # Sender: span.summary.sentby > span.text
                # Time: span.time
                # ID: data-notice attribute on the text spans
                
                subject_span = item.select_one('span.summary:not(.sentby) span.text')
                sender_span = item.select_one('span.summary.sentby span.text')
                time_span = item.select_one('span.time')
                
                msg_id = subject_span.get('data-notice') if subject_span else None
                subject = subject_span.get_text(strip=True) if subject_span else "(No Subject)"
                sender = sender_span.get_text(strip=True) if sender_span else "Unknown"
                date_str = time_span.get_text(strip=True) if time_span else ""
                
                # Check for unread indicators?
                # User example showed <i class='priority-icon ... red'>
                # Often standard class is used for row styling, but let's just print basic info first.
                # We can't easily determine Read/Unread without more info on classes.
                # Assuming all are displayed.
                
                messages.append({
                    'noticeId': msg_id,
                    'subject': subject,
                    'sender': sender,
                    'date': date_str
                })
                
                print(f"{i+1}. {sender}: {subject} ({date_str})")

            print("\nOptions:")
            print("  Number (1-10): Read Message")
            print("  n: Next Page")
            print("  p: Previous Page")
            print("  b: Back to Menu")
            
            choice = input("Enter choice: ").strip().lower()
            
            if choice == 'n':
                page += 1
            elif choice == 'p':
                if page > 0:
                    page -= 1
                else:
                    print("Already on first page.")
            elif choice == 'b' or choice == 'q':
                return
            elif choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(messages):
                    selected_msg = messages[idx]
                    msg_id = selected_msg.get('NoticeId') or selected_msg.get('noticeId')
                    
                    # 2. Read Message
                    print(f"\nLoading message {msg_id}...")
                    
                    detail_payload = {
                        "noticeId": msg_id,
                        "isforward": False,
                        "isreply": False,
                        "isreplyall": False
                    }
                    
                    # Using the unified action URL
                    detail_resp = session.post(message_action_url, headers=headers, json=detail_payload)
                    if detail_resp.status_code == 200:
                        detail_json = detail_resp.json()
                        detail_d = detail_json.get('d')
                        if isinstance(detail_d, str):
                            detail_d = json.loads(detail_d)
                        
                        # Assuming detail_d is the message object
                        body = detail_d.get('Body') or detail_d.get('body') or ""
                        subject_full = detail_d.get('Subject') or detail_d.get('subject')
                        
                        # Clean HTML from body, preserving newlines
                        # Use BeautifulSoup to handle <br>, <p>, etc.
                        body_soup = BeautifulSoup(body, 'html.parser')
                        
                        # Replace <br> with newlines explicitly before get_text if needed, 
                        # but get_text(separator='\n') usually handles block elements well.
                        # However, <br> is inline, so let's handle it.
                        for br in body_soup.find_all("br"):
                            br.replace_with("\n")
                            
                        # Extract text with separators for block elements
                        clean_body = body_soup.get_text(separator='\n', strip=True)
                        
                        print("\n" + "="*30)
                        print(f"Subject: {subject_full}")
                        print("="*30)
                        print(clean_body)
                        print("="*30 + "\n")
                        
                        input("Press Enter to return...")
                        
                        # 3. Mark as Read
                        mark_read_payload = {
                            "noticeIds": msg_id, # Sending single int as per user payload example
                            "status": "read",
                            "tab": "inbox"
                        }
                        
                        # Using the SAME URL for marking read
                        session.post(message_action_url, headers=headers, json=mark_read_payload)
                        # We don't strictly care if this fails, but it updates status for next view.
                        
                    else:
                        print(f"Failed to load message. Code: {detail_resp.status_code}")
                else:
                    print("Invalid message number.")
            else:
                print("Invalid command.")

        except Exception as e:
            print(f"Error: {e}")
            return
    

def info():
    get_version_url = "https://raw.githubusercontent.com/SaksornSea/Engage-CLI/refs/heads/main/version.txt"
    
    latest_version = "Checking..."
    update_available = ""

    try:
        # Short timeout to avoid hanging the UI
        resp = requests.get(get_version_url, timeout=3)
        if resp.status_code == 200:
            latest_version = resp.text.strip()
            # Basic string comparison (assumes format X.Y matches)
            if latest_version != version:
                 update_available = "\033[93mUpdate available! :O\033[0m" # Yellow warning
            else:
                 update_available = "\033[32mYou are up to date! :D\033[0m" # Green success
            latest_version = f"v{latest_version}"
        else:
            latest_version = "Error"
            update_available = "\033[31mCould not check. :(\033[31m"
    except Exception:
         latest_version = "Offline"
         update_available = "\033[31mNo connection. :/\033[31m"
    
    # ASCII Art for Engage Logo
    # Blue top, Green bottom gradient simulation
    
    b = "\033[34m" # Blue
    c = "\033[36m" # Green
    r = "\033[0m"  # Reset
    
    logo = f"""
   {b}-===                                                                 ====  {r}              Engage CLI v{version}
   {b}======                                                             -=====- {r}              https://sea.navynui.cc/tools/engage/
  {b}-========                                                          ======== {r}              Programed in Python
  {b}==========-                                                      ==+======= {r}              By Sea :)
  {b}=====+++++++                                                   =++++++=====-{r}              Made with the help of Gemini :D
  {b}==+=++++++++++                                               =++++++++++===-{r}              Logged in as: {username}
  {b}=+++++++++++++++                                           =+++++++++++++++={r}              Newest version available: {latest_version}
  {b}=++++++++++++++++=                                       =+++++++++++++++++={r}              {update_available}
  {b}=++++++++++++++++++=                                   ++++++++++++++++++++={r}
  {b}+++++++++++++++++***++                               ++*+*+++++++++++++++++={r}
  {b}=+++++++++++++*+*******+                           ++*******+++++++++++++++ {r}
  {b}=+++++++++++*+***********+                       ++***********+*++++++++++= {r}
   {b}++++++++*+***********#*##*+                    +###*#***********+++++++++= {r}
   {b}=+++++*+***********########*+                #########************+*+++++  {r}
    {b}++*+***********#############*+            ##############************+++-  {r}
     {b}+***********#################*         +#################***********++   {r}
     {b}=+*******######################       *#####################*******++    {r}
       {b}+***##########################     +########################*****+     {r}
        {b}+*#*#########################+    ############################+       {r}
         {b}+*###########################   =##########################*+        {r}
           {b}+*#########################   +########################*+          {r}
              {b}*#######################   +#######################             {r}
                {c}+{b}#####################   +####################{c}+         {r}
               {c}=++**{b}#################+    ##################{c}*++=        {r}
              {c}=++++***{b}###############     *###############{c}**+++++       {r}
             {c}=++++++****{b}############+      ############{c}****+*+++++      {r}
            {c}=++++++++*****{b}##########       +#########{c}*****+++++++++     {r}
           {c}=++++++++++++*****{b}######         +######{c}*****+++++++++++=    {r}
           {c}=++++++++++++++*****{b}##*           =###{c}***+++++++++++++++=    {r}
           {c}=++++++++++++++++++*+=              ++++++++++++++++++++=          {r}
           {c}-+++++++++++++++++++                 =++++++++++++++++++=          {r}
            {c}=++++++++++++++++=                    ++++++++++++++++=           {r}
             {c}=++++++++++++++                       =+++++++++++++=            {r}
              {c}==++++++++++=                         =++++++++++==             {r}
                {c}==++++++==                            =++++++===              {r}
                  {c}===+==                               ==+===                 {r}
    """
    print(logo)

def getpicture():
    print("Your profile picture is at:", base_url + photo_src)

base_url = f'https://{subdomain}.engagehosted.com'

# Global state
session = None
pid = None
photo_src = None
username = ""
password = ""
is_parent = False
ENABLE_PDF_GEN = True

while True:
    print("\n" + "="*50)
    print("Engage CLI - Account Selection")
    print("="*50)

    if not accounts:
        print("No accounts found in configuration file.")

    for i, acc in enumerate(accounts):
        print(f"{i+1}. {acc.get('name', 'Unknown')} ({acc.get('username')})")

    new_acc_index = len(accounts) + 1
    guest_mode_index = len(accounts) + 2

    print(f"{new_acc_index}. Create New Account")
    print(f"{guest_mode_index}. Guest Mode")
    print(f"{guest_mode_index + 1}. Exit")

    account_selected = False

    while not account_selected:
        try:
            choice_input = input("Enter choice: ")
            if not choice_input:
                 continue
            choice = int(choice_input)
            
            if choice == guest_mode_index + 1:
                print("Goodbye!")
                exit(0)
            
            if 1 <= choice <= len(accounts):
                # Existing account
                username = accounts[choice-1].get('username')
                password = accounts[choice-1].get('password')
                account_selected = True
            elif choice == new_acc_index:
                # Create New Account
                name = input("Enter Name for new account (Example: My Account): ")
                user = input("Enter Username: ")
                pwd = input("Enter Password: ")
                
                with open('engage.config', 'a') as f:
                    if os.path.exists('engage.config') and os.path.getsize('engage.config') > 0:
                        f.write("\n")
                    f.write(f"acc{len(accounts)}:\n")
                    f.write(f"name: {name}\n")
                    f.write(f"username: {user}\n")
                    f.write(f"password: {pwd}\n")
                
                # Update runtime list
                accounts.append({'name': name, 'username': user, 'password': pwd})
                
                username = user
                password = pwd
                print(f"Account '{name}' saved!")
                account_selected = True
            elif choice == guest_mode_index:
                # Guest Mode
                username = input("Enter Username: ")
                password = input("Enter Password: ")
                account_selected = True
            else:
                print("Invalid choice.")
        except ValueError:
             print("Invalid input. Please enter a number.")

    # Login Process
    main_url = f'{base_url}/Login.aspx?ReturnUrl=%2fDefault.aspx'
    get_other_cookies_url = f'{base_url}/Default.aspx'
    login_url = f'{base_url}/Login.aspx'
    vle_url = f'{base_url}/vle/default.aspx'
    
    custom_user_agent = 'Engage CLI(' + version + ")"
    # custom_user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36'

    session = requests.Session()
    session.headers.update({'User-Agent': custom_user_agent})

    try:
        main_response = session.get(main_url)
        
        # Get cookies
        get_other_cookies_response = session.get(get_other_cookies_url)
        
        # Extract ViewState
        viewstate_match = re.search(r'name="__VIEWSTATE" id="__VIEWSTATE" value="(.*?)"', get_other_cookies_response.text)
        viewstategenerator_match = re.search(r'name="__VIEWSTATEGENERATOR" id="__VIEWSTATEGENERATOR" value="(.*?)"', get_other_cookies_response.text)
        viewstateencrypted_match = re.search(r'name="__VIEWSTATEENCRYPTED" id="__VIEWSTATEENCRYPTED" value="(.*?)"', get_other_cookies_response.text)
        eventvalidation_match = re.search(r'name="__EVENTVALIDATION" id="__EVENTVALIDATION" value="(.*?)"', get_other_cookies_response.text)

        __VIEWSTATE = viewstate_match.group(1) if viewstate_match else ""
        __VIEWSTATEGENERATOR = viewstategenerator_match.group(1) if viewstategenerator_match else ""
        __VIEWSTATEENCRYPTED = viewstateencrypted_match.group(1) if viewstateencrypted_match else ""
        __EVENTVALIDATION = eventvalidation_match.group(1) if eventvalidation_match else ""

        login_data = {
            'ctl00_ctl13_TSSM': ';Telerik.Web.UI, Version=2021.3.1111.45, Culture=neutral, PublicKeyToken=121fae78165ba3d4:en-GB:b406acc5-0028-4c73-8915-a9da355d848a:1c2121e',
            'ctl00_ScriptManager1_HiddenField': '',
            '__LASTFOCUS': '',
            '__EVENTTARGET': '',
            '__EVENTARGUMENT': '',
            '__VIEWSTATE': __VIEWSTATE,
            '__VIEWSTATEGENERATOR': __VIEWSTATEGENERATOR,
            '__VIEWSTATEENCRYPTED': __VIEWSTATEENCRYPTED,
            '__EVENTVALIDATION': __EVENTVALIDATION,
            'ctl00$hdnUnsavedDataWarningEnabled': 'false',
            'ctl00$hdnStaffRegisterInFlag': 'in',
            'ctl00$hdnPageName': 'Login.aspx',
            'ctl00$PageContent$loginControl$hdnMaxLoginAttempts': '0',
            'ctl00$PageContent$loginControl$hdnToken': '',
            'ctl00$PageContent$loginControl$hdnLinkAccount': '0',
            'ctl00$PageContent$loginControl$hdnIsPWALogin': 'false',
            'ctl00$PageContent$loginControl$hdnIsPupilPortal': '0',
            'ctl00$PageContent$loginControl$languageSelect$ddlLanguage': 'UK English',
            'ctl00_PageContent_loginControl_languageSelect_ddlLanguage_ClientState': '',
            'ctl00$PageContent$loginControl$txtUN': username,
            'ctl00$PageContent$loginControl$txtPwd': password,
            'ctl00$PageContent$loginControl$txtMFA': '',
            'ctl00$PageContent$loginControl$btnLogin': 'Login',
            'ctl00$ddlReason': 'Select',
            'ctl00_ddlReason_ClientState': '',
            'ctl00$txtNotes': ''
        }

        print("Sending login request...")
        login_response = session.post(login_url, headers={'Referer': login_url}, data=login_data)
        
        vle_response = session.get(vle_url)
        
        # Updated Regex to handle &amp; in URL
        src_match = re.search(r'src="(/DBImage\.axd\?type=pupil&(?:amp;)?pid=[^"]+)"', vle_response.text)
        
        found_pid = False
        
        if src_match:
            photo_src = src_match.group(1)
            pid_match = re.search(r'pid=([^&"]+)', photo_src)
            if pid_match:
                pid = pid_match.group(1)
                print(f"Login successful! (Pupil) PID: {pid}")
                found_pid = True
                is_parent = False

        if not found_pid:
            # Check for Parent Account Image/Links via RAW REGEX
            # BeautifulSoup might fail on the malformed HTML (<div inside table)
            # We look for the Encrypted PID pattern: pid=... or ID=...
            # The PID generally looks like a base64 string with %3d (encoded =) at the end.
            
            # Pattern to match: pid= (or ID= or pupilID=) followed by non-quote/ampersand chars
            # We specifically target the long encrypted string format.
            
            print("DEBUG: Attempting raw regex search for PID...")
            
            # Common patterns in the snippet:
            # src="/DBImage.axd?type=pupil&amp;pid=..."
            # href="...Details.aspx?ID=..."
            # href="...Schedules.aspx?pupilID=..."
            
            # Regex 1: DBImage src
            # Allow for &amp; or &
            dbimage_match = re.search(r'src="[^"]*DBImage\.axd[^"]*(?:&|&amp;)pid=([^&"]+)', vle_response.text)
            
            if dbimage_match:
                pid = dbimage_match.group(1)
                # Construct photo_src manually since we have the PID
                photo_src = f"/DBImage.axd?type=pupil&pid={pid}"
                print(f"DEBUG: Found PID via DBImage Regex: {pid}")
                print(f"Login successful! (Parent via Regex) PID: {pid}")
                found_pid = True
                is_parent = True
            
            if not found_pid:
                 # Regex 2: Try specific ID link (View Details)
                 link_match = re.search(r'ContactDetails\.aspx\?ID=([^&"]+)', vle_response.text)
                 if link_match:
                     pid = link_match.group(1)
                     photo_src = f"/DBImage.axd?type=pupil&pid={pid}"
                     print(f"DEBUG: Found PID via Contact Link: {pid}")
                     print(f"Login successful! (Parent via Link) PID: {pid}")
                     found_pid = True
                     is_parent = True
                     
            if not found_pid:
                # Debug output if totally failed
                print("DEBUG: All regex searches failed.")
                # print(vle_response.text[:500]) # Print first 500 chars to check if we even got content
                 
        if not found_pid:
            print("Login failed. Please check your credentials.")
            continue
            
    except Exception as e:
        print(f"An error occurred during login: {e}")
        continue

    # Action Loop
    while True:
        print("\n" + "-"*100)

        
        print("\n" + "="*50)
        print("Engage CLI - Action Selection")
        print("="*50)
        print("1. Get your scores")
        print("2. Get your details")
        print("3. Get your assessment reports")
        print("4. Get your weekly schedule")
        print("5. Get your inbox")
        print("6. Get your profile picture (for fun :D)")
        print("7. Switch accounts")
        print("8. Info and Check for updates")
        print("9. Exit")

        try:
            choice_input = input("Enter your choice(1-9): ")
            print("-"*100 + "\n")
            if not choice_input: continue
            choice = int(choice_input)
            
            if choice == 1: getscores()
            elif choice == 2: getdetails()
            elif choice == 3: getassessment()
            elif choice == 4: getschedule()
            elif choice == 5: getinbox()
            elif choice == 6: getpicture()
            elif choice == 7: break # Break inner loop, go to outer loop (Select/Switch Account)
            elif choice == 8: info()
            elif choice == 9: 
                print("Goodbye!")
                exit(0)
            else: print("Invalid choice. Please try again.")
        except ValueError:
            print("Invalid input.")
