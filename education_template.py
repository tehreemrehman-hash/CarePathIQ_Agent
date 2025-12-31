"""
Education Module Template Generator
Creates customizable interactive education modules with quizzes and certificates
"""

import json
from datetime import datetime


def create_education_module_template(
    condition: str,
    topics: list = None,
    organization: str = "CarePathIQ",
    learning_objectives: list = None,
    target_audience: str = "Clinical Team",
    require_100_percent: bool = True,
    care_setting: str = None,
    role_context: dict = None,
    role_statement: str = None,
    genai_client=None
) -> str:
    """
    Create a complete, customizable education module template with certificate generation.
    Content and structure adapt based on LLM inference of target audience focus areas.
    
    Args:
        condition: Topic/condition name
        topics: List of dicts with keys:
                - 'title': Module title
                - 'content': HTML content
                - 'learning_objectives': List of learning objectives
                - 'quiz': List of quiz questions (dicts with 'question', 'options', 'correct', 'explanation')
                - 'time_minutes': Estimated time to complete
        organization: Organization name for certificate
        learning_objectives: Overall course learning objectives
        target_audience: Target audience for the module (free-text) for LLM-based inference
        require_100_percent: If True, require 100% quiz completion for certificate
        care_setting: Care setting/environment for the condition (e.g., "Emergency Department")
        role_context: Dict with role-specific metadata (role_type, depth_level, expectations, etc.)
        role_statement: Explicit statement about learner role in pathway
        genai_client: Optional Google Generative AI client for audience inference
        
    Returns:
        Complete standalone HTML string with audience-adapted content
    """
    
    if topics is None:
        topics = []

    # Audience inference to tailor tone/detail; falls back gracefully if helper unavailable
    try:
        from phase5_helpers import infer_audience_from_description
        audience_metadata = infer_audience_from_description(target_audience, genai_client)
    except Exception:
        audience_metadata = {
            "detail_level": "moderate",
            "emphasis_areas": ["workflow", "safety", "competency"],
            "tone": "technical_detailed"
        }
    detail_level = audience_metadata.get("detail_level", "moderate")
    emphasis_areas = audience_metadata.get("emphasis_areas", [])
    
    # Calculate total time from topics
    total_time_minutes = sum(topic.get('time_minutes', 5) for topic in topics) if topics else 15
    
    # Build professional, pathway-focused header
    condition_display = condition.strip() if condition else "Pathway"
    condition_display = condition_display.title()
    care_setting_display = care_setting.strip().title() if care_setting else ""
    
    # Dynamic title based on Phase 1 inputs and role context
    if care_setting_display:
        header_display = f"{condition_display} Pathway — {care_setting_display}"
    else:
        header_display = f"{condition_display} Pathway"
    
    # Use role statement for course intro if provided
    course_intro_statement = role_statement if role_statement else f"This interactive course will guide you through evidence-based learning on {condition} in {care_setting if care_setting else 'clinical practice'}. Each module includes content, key takeaways, and a brief assessment. Designed specifically for {target_audience}."

    # Provide a minimal default module if none supplied (ensures Start works)
    if not topics:
        topics = [
            {
                "title": f"Module 1: {condition_display} essentials",
                "content": f"<p>Overview of the {condition_display.lower()} pathway in {care_setting or 'clinical practice'}.</p>",
                "learning_objectives": [
                    f"Describe the goals of the {condition_display} pathway",
                    f"Outline the care flow for {condition_display.lower()} in {care_setting or 'your setting'}",
                    "Identify where to find supporting tools and documentation"
                ],
                "quiz": [
                    {
                        "question": "What is the primary aim of this pathway?",
                        "options": [
                            "Standardize care and improve safety",
                            "Increase paperwork",
                            "Delay treatment",
                            "Remove clinical judgment"
                        ],
                        "correct": 0,
                        "explanation": "Clinical pathways standardize high-quality care and improve safety/throughput."
                    }
                ],
                "time_minutes": 5
            }
        ]
    
    if learning_objectives is None:
        learning_objectives = [
            f"Understand the clinical presentation of {condition}",
            f"Apply evidence-based management strategies for {condition}",
            "Recognize complications and adverse outcomes",
            "Communicate effectively with the healthcare team"
        ]
    
    # Safely serialize to JSON - use separators to avoid extra whitespace
    # Ensure ASCII to avoid unicode issues in JavaScript
    topics_json = json.dumps(topics, ensure_ascii=True, separators=(',', ':'))
    obj_json = json.dumps(learning_objectives, ensure_ascii=True, separators=(',', ':'))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    emphasis_text = ", ".join(emphasis_areas) if emphasis_areas else ""
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Education Module: {header_display}</title>
    <style>
        :root {{
            --brown: #5D4037;
            --brown-dark: #3E2723;
            --teal: #A9EED1;
            --light-gray: #f5f5f5;
            --border-gray: #ddd;
            --success: #d4edda;
            --success-text: #155724;
            --error: #f8d7da;
            --error-text: #721c24;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        html, body {{
            width: 100%;
            height: 100%;
        }}

        body {{
            font-family: 'Segoe UI', Tahoma, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #f5f5f5 0%, #e8e8e8 100%);
        }}

        .container {{
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
        }}

        .main-content {{
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }}

        .header {{
            background: linear-gradient(135deg, var(--brown) 0%, var(--brown-dark) 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}

        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}

        .header-subtitle {{
            font-size: 1.2em;
            opacity: 0.9;
        }}

        .progress-section {{
            background: var(--light-gray);
            padding: 20px 40px;
            border-bottom: 1px solid var(--border-gray);
        }}

        .progress-label {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
            font-weight: 600;
        }}

        .progress-bar {{
            width: 100%;
            height: 12px;
            background: var(--border-gray);
            border-radius: 6px;
            overflow: hidden;
        }}

        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, var(--teal) 0%, var(--brown) 100%);
            transition: width 0.3s ease;
            border-radius: 6px;
        }}

        .breadcrumb {{
            padding: 15px 40px;
            background: white;
            border-bottom: 1px solid var(--border-gray);
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 0.9em;
            color: #666;
            flex-wrap: wrap;
        }}

        .breadcrumb-item {{
            display: flex;
            align-items: center;
        }}

        .breadcrumb-item.active {{
            color: var(--brown);
            font-weight: 600;
        }}

        .breadcrumb-divider {{
            margin: 0 5px;
            color: #999;
        }}

        .content-wrapper {{
            display: flex;
            min-height: 600px;
        }}

        .sidebar {{
            width: 250px;
            background: var(--light-gray);
            border-right: 1px solid var(--border-gray);
            overflow-y: auto;
            padding: 0;
        }}

        .sidebar-header {{
            padding: 20px;
            background: white;
            border-bottom: 1px solid var(--border-gray);
            font-weight: 600;
            color: var(--brown-dark);
        }}

        .module-list {{
            list-style: none;
        }}

        .module-item {{
            padding: 15px 20px;
            border-bottom: 1px solid var(--border-gray);
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            gap: 10px;
            background: white;
        }}

        .module-item:hover {{
            background: var(--light-gray);
            border-left: 4px solid var(--teal);
            padding-left: 16px;
        }}

        .module-item.active {{
            background: white;
            color: var(--brown);
            border-left: 4px solid var(--teal);
            padding-left: 16px;
            font-weight: 600;
        }}

        .module-status {{
            display: inline-block;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background: var(--border-gray);
            text-align: center;
            line-height: 20px;
            font-size: 0.8em;
            flex-shrink: 0;
        }}

        .module-status.completed {{
            background: var(--teal);
            color: var(--brown-dark);
            font-weight: bold;
        }}

        .module-status.current {{
            background: var(--brown);
            color: white;
        }}

        .main-area {{
            flex: 1;
            padding: 40px;
            overflow-y: auto;
        }}

        .module-content {{
            display: none;
        }}

        .module-content.active {{
            display: block;
            animation: slideIn 0.3s ease;
        }}

        @keyframes slideIn {{
            from {{
                opacity: 0;
                transform: translateY(10px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}

        .module-header {{
            margin-bottom: 30px;
        }}

        .module-header h2 {{
            color: var(--brown-dark);
            font-size: 2em;
            margin-bottom: 10px;
        }}

        .learning-objectives {{
            background: var(--light-gray);
            padding: 20px;
            border-radius: 6px;
            margin: 20px 0;
            border-left: 4px solid var(--teal);
        }}

        .learning-objectives h3 {{
            color: var(--brown);
            margin-bottom: 10px;
        }}

        .learning-objectives ul {{
            list-style: none;
            margin-left: 20px;
        }}

        .learning-objectives li {{
            margin: 8px 0;
            padding-left: 20px;
            position: relative;
        }}

        .learning-objectives li:before {{
            content: "✓";
            position: absolute;
            left: 0;
            color: var(--teal);
            font-weight: bold;
        }}

        .content-body {{
            font-size: 1.05em;
            line-height: 1.8;
            margin: 20px 0;
        }}

        .content-body h3 {{
            color: var(--brown);
            margin: 25px 0 10px 0;
        }}

        .content-body p {{
            margin: 15px 0;
        }}

        .content-body ul, .content-body ol {{
            margin: 15px 0 15px 30px;
        }}

        .content-body li {{
            margin: 8px 0;
        }}

        .callout {{
            background: #e3f2fd;
            border-left: 4px solid #2196F3;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }}

        .callout.warning {{
            background: #fff3e0;
            border-left-color: #ff9800;
        }}

        .callout.important {{
            background: #fce4ec;
            border-left-color: #c2185b;
        }}

        .quiz-section {{
            background: var(--light-gray);
            padding: 25px;
            border-radius: 6px;
            margin-top: 30px;
        }}

        .quiz-section h3 {{
            color: var(--brown-dark);
            margin-bottom: 20px;
        }}

        .quiz-question {{
            background: white;
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 6px;
            border: 1px solid var(--border-gray);
        }}

        .quiz-question.answered {{
            border-left: 4px solid var(--teal);
        }}

        .question-text {{
            font-weight: 600;
            margin-bottom: 15px;
            color: var(--brown-dark);
        }}

        .quiz-options {{
            display: flex;
            flex-direction: column;
            gap: 10px;
        }}

        .quiz-option {{
            display: flex;
            align-items: flex-start;
            gap: 10px;
            cursor: pointer;
            padding: 10px;
            border-radius: 4px;
            transition: background 0.2s ease;
        }}

        .quiz-option:hover {{
            background: var(--light-gray);
        }}

        .quiz-option input[type="radio"] {{
            margin-top: 2px;
            cursor: pointer;
            flex-shrink: 0;
        }}

        .quiz-option label {{
            margin: 0;
            cursor: pointer;
            flex: 1;
        }}

        .quiz-feedback {{
            margin-top: 15px;
            padding: 15px;
            border-radius: 4px;
            display: none;
            font-weight: 600;
        }}

        .quiz-feedback.show {{
            display: block;
        }}

        .quiz-feedback.correct {{
            background: var(--success);
            color: var(--success-text);
            border: 1px solid #c3e6cb;
        }}

        .quiz-feedback.incorrect {{
            background: var(--error);
            color: var(--error-text);
            border: 1px solid #f5c6cb;
        }}

        .navigation {{
            display: flex;
            gap: 15px;
            margin-top: 30px;
            justify-content: space-between;
            padding-top: 20px;
            border-top: 1px solid var(--border-gray);
        }}

        .nav-button {{
            flex: 1;
            padding: 12px 20px;
            background: var(--brown);
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 1em;
            font-weight: 600;
            transition: background 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }}

        .nav-button:hover {{
            background: var(--brown-dark);
        }}

        .nav-button:disabled {{
            background: var(--border-gray);
            cursor: not-allowed;
            opacity: 0.6;
        }}

        .certificate {{
            display: none;
            page-break-after: always;
        }}

        .certificate.show {{
            display: block;
        }}

        .certificate-container {{
            background: linear-gradient(135deg, var(--teal) 0%, white 100%);
            padding: 50px;
            border: 6px solid var(--brown);
            border-radius: 10px;
            margin: 30px 0;
            text-align: center;
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.15);
        }}

        .certificate-content {{
            background: white;
            padding: 50px;
            border: 3px dashed var(--brown);
            border-radius: 8px;
            position: relative;
        }}

        .certificate-decoration {{
            position: absolute;
            top: 15px;
            font-size: 2em;
        }}

        .certificate-decoration.left {{
            left: 15px;
        }}

        .certificate-decoration.right {{
            right: 15px;
        }}

        .certificate-title {{
            font-size: 2.5em;
            color: var(--brown-dark);
            margin-bottom: 15px;
            font-weight: bold;
        }}

        .certificate-subtitle {{
            font-size: 1.2em;
            color: #666;
            margin-bottom: 30px;
        }}

        .certificate-recipient {{
            margin: 30px 0;
        }}

        .certificate-recipient-label {{
            font-size: 1em;
            color: #666;
        }}

        #recipientName {{
            font-size: 2em;
            border: none;
            border-bottom: 2px solid var(--brown);
            text-align: center;
            width: 100%;
            max-width: 500px;
            margin: 10px auto;
            padding: 10px 0;
            font-weight: bold;
            color: var(--brown-dark);
        }}

        .certificate-text {{
            font-size: 1.1em;
            color: #333;
            margin: 15px 0;
            line-height: 1.6;
        }}

        .certificate-condition {{
            font-size: 1.5em;
            color: var(--brown);
            font-weight: bold;
            margin: 20px 0;
        }}

        .certificate-meta {{
            margin-top: 40px;
            color: #666;
            font-size: 0.95em;
        }}

        .certificate-id {{
            font-size: 0.85em;
            color: #999;
            margin-top: 15px;
            font-family: monospace;
        }}

        .certificate-actions {{
            display: flex;
            gap: 10px;
            justify-content: center;
            margin-top: 30px;
            flex-wrap: wrap;
        }}

        .btn {{
            padding: 12px 24px;
            background: var(--brown);
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-weight: 600;
            transition: background 0.3s ease;
        }}

        .btn:hover {{
            background: var(--brown-dark);
        }}

        .btn.secondary {{
            background: var(--teal);
            color: var(--brown-dark);
        }}

        .btn.secondary:hover {{
            background: #92d5b8;
        }}

        .course-intro {{
            background: var(--light-gray);
            padding: 30px;
            border-radius: 6px;
            margin-bottom: 30px;
            border-left: 4px solid var(--teal);
        }}

        .course-intro h3 {{
            color: var(--brown-dark);
            margin-bottom: 10px;
        }}

        .course-intro ul {{
            list-style: none;
            margin-left: 20px;
        }}

        .course-intro li {{
            margin: 8px 0;
            padding-left: 20px;
            position: relative;
        }}

        .course-intro li:before {{
            content: "→";
            position: absolute;
            left: 0;
            color: var(--teal);
            font-weight: bold;
        }}

        .completion-banner {{
            background: linear-gradient(135deg, var(--teal) 0%, #92d5b8 100%);
            color: var(--brown-dark);
            padding: 20px;
            border-radius: 6px;
            text-align: center;
            margin-bottom: 20px;
            font-weight: 600;
            display: none;
        }}

        .completion-banner.show {{
            display: block;
        }}

        .footer {{
            text-align: center;
            padding: 30px 40px;
            background: white;
            border-top: 1px solid var(--border-gray);
            color: #666;
            font-size: 0.9em;
        }}

        .footer a {{
            color: var(--brown);
            text-decoration: none;
        }}

        .footer a:hover {{
            text-decoration: underline;
        }}

        @media (max-width: 768px) {{
            .content-wrapper {{
                flex-direction: column;
            }}

            .sidebar {{
                width: 100%;
                max-height: 200px;
                border-right: none;
                border-bottom: 1px solid var(--border-gray);
            }}

            .main-area {{
                padding: 20px;
            }}

            .header {{
                padding: 20px;
            }}

            .header h1 {{
                font-size: 1.5em;
            }}

            .module-item {{
                display: inline-block;
                width: calc(50% - 5px);
                margin-right: 10px;
                border-bottom: 1px solid var(--border-gray);
            }}

            .nav-button {{
                flex-direction: column;
            }}

            .certificate-title {{
                font-size: 1.5em;
            }}

            .certificate-condition {{
                font-size: 1.2em;
            }}
        }}

        @media print {{
            body {{
                background: white;
            }}

            .main-content {{
                box-shadow: none;
            }}

            .sidebar,
            .breadcrumb,
            .progress-section,
            .navigation,
            .certificate-actions,
            .btn:not(.hidden) {{
                display: none;
            }}

            .main-area {{
                padding: 0;
            }}

            .certificate {{
                page-break-before: always;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="main-content">
            <!-- Header -->
            <div class="header">
                <h1>{header_display}</h1>
                <div class="header-subtitle">Interactive Pathway-Based Learning Module</div>
            </div>

            <!-- Progress Section -->
            <div class="progress-section">
                <div class="progress-label">
                    <span>Course Progress</span>
                    <span id="progressPercent">0%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" id="progressFill" style="width: 0%"></div>
                </div>
                <div style="margin-top: 10px; font-size: 0.9em; color: #666;">
                    <span id="modulesCompleted">0</span> of <span id="modulesTotal">0</span> modules completed
                </div>
            </div>

            <!-- Breadcrumb -->
            <div class="breadcrumb">
                <span class="breadcrumb-item active">Pathway</span>
                <span class="breadcrumb-divider">/</span>
                <span class="breadcrumb-item" id="breadcrumbTitle">{header_display}</span>
            </div>

            <!-- Content Wrapper -->
            <div class="content-wrapper">
                <!-- Sidebar Navigation -->
                <div class="sidebar">
                    <div class="sidebar-header">Course Modules</div>
                    <ul class="module-list" id="moduleList"></ul>
                </div>

                <!-- Main Content Area -->
                <div class="main-area">
                    <!-- Course Introduction (shown on start) -->
                    <div id="courseIntro" class="module-content active">
                        <div class="module-header">
                            <h2>Welcome</h2>
                        </div>

                        <div class="course-intro">
                            <h3>Course Learning Objectives</h3>
                            <ul id="learningObjectivesList"></ul>
                        </div>

                        <p style="margin: 20px 0; font-size: 1.1em;">
                            {course_intro_statement}
                        </p>

                        <p style="margin: 20px 0; color: #666;">
                            <strong>Time to Complete:</strong> {total_time_minutes} minutes ({len(topics)} modules)
                        </p>

                        <button class="nav-button" onclick="startCourse()" style="width: auto; margin-top: 20px;">
                            Start Course →
                        </button>
                    </div>

                    <!-- Module Content Templates -->
                    <div id="modulesContainer"></div>

                    <!-- Certificate (shown on completion) -->
                    <div id="certificateSection" class="certificate">
                        <div class="certificate-container">
                            <div class="certificate-decoration left">★</div>
                            <div class="certificate-decoration right">★</div>

                            <div class="certificate-content">
                                <div class="certificate-title">Certificate of Completion</div>
                                <div class="certificate-subtitle">This certifies that</div>

                                <div class="certificate-recipient">
                                    <input type="text" id="recipientName" placeholder="Your Name" autofocus>
                                </div>

                                <div class="certificate-text">
                                    has successfully completed the
                                </div>

                                <div class="certificate-condition">{condition}</div>

                                <div class="certificate-text">
                                    Education Module offered by
                                </div>

                                <div style="font-weight: bold; color: var(--brown); margin: 15px 0; font-size: 1.1em;">
                                    {organization}
                                </div>

                                <div class="certificate-meta">
                                    <p style="margin: 10px 0;">
                                        Date of Completion: <strong id="completionDate"></strong>
                                    </p>
                                    <div class="certificate-id">
                                        Certificate ID: <span id="certId"></span>
                                    </div>
                                    <p style="margin-top: 15px; font-size: 0.9em;">
                                        This certificate serves as a record of educational completion
                                    </p>
                                </div>
                            </div>
                        </div>

                        <div class="certificate-actions">
                            <button class="btn" onclick="printCertificate()">Print Certificate</button>
                            <button class="btn secondary" onclick="downloadCertificateSVG()">Download Certificate</button>
                            <button class="btn secondary" onclick="emailCertificate()">Email Certificate</button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Footer -->
            <div class="footer">
                <p>
                    <strong>CarePathIQ</strong> © 2024 by Tehreem Rehman |
                    Licensed under <a href="https://creativecommons.org/licenses/by-sa/4.0/" target="_blank">CC BY-SA 4.0</a>
                </p>
            </div>
        </div>
    </div>

    <script>
        const TOPICS = {topics_json};
        const LEARNING_OBJECTIVES = {obj_json};
        const CONDITION = "{condition}";
        const ORGANIZATION = "{organization}";
        const TIMESTAMP = "{timestamp}";

        let completedModules = {{}};
        let currentModuleIdx = -1;
        let allAnswered = {{}};

        // Fallback: ensure at least one module exists even if upstream provided none
        function ensureTopics() {{
            if (!Array.isArray(TOPICS) || TOPICS.length === 0) {{
                // reset and push a minimal default module
                while (TOPICS.length) {{ TOPICS.pop(); }}
                TOPICS.push({{
                    title: `Module 1: ${{CONDITION}} overview`,
                    content: `<p>Overview of the ${{CONDITION}} pathway.</p>`,
                    learning_objectives: [
                        `Describe the goals of the ${{CONDITION}} pathway`,
                        `Outline the care flow for ${{CONDITION}}`,
                        `Identify supporting tools and documentation`
                    ],
                    quiz: [{
                        question: `What is the primary aim of this pathway?`,
                        options: [
                            "Standardize care and improve safety",
                            "Increase paperwork",
                            "Delay treatment",
                            "Remove clinical judgment"
                        ],
                        correct: 0,
                        explanation: "Clinical pathways standardize high-quality care and improve safety/throughput."
                    }],
                    time_minutes: 5
                }});
            }
        }}

        // Initialize on page load
        document.addEventListener('DOMContentLoaded', function() {{
            ensureTopics();
            initializeCourse();
            generateCertificateID();
        }});

        function initializeCourse() {{
            // Populate learning objectives
            const objList = document.getElementById('learningObjectivesList');
            LEARNING_OBJECTIVES.forEach(obj => {{
                const li = document.createElement('li');
                li.textContent = obj;
                objList.appendChild(li);
            }});

            // Populate module list and content
            const moduleList = document.getElementById('moduleList');
            const modulesContainer = document.getElementById('modulesContainer');

            TOPICS.forEach((topic, idx) => {{
                // Add to sidebar
                const li = document.createElement('li');
                li.className = 'module-item';
                li.innerHTML = `
                    <div class="module-status" id="status_${{idx}}">${{idx + 1}}</div>
                    <span id="label_${{idx}}">Module ${{idx + 1}}</span>
                `;
                li.onclick = () => switchModule(idx);
                moduleList.appendChild(li);

                // Create module content
                const moduleDiv = document.createElement('div');
                moduleDiv.className = 'module-content';
                moduleDiv.id = `module_${{idx}}`;

                let content = `
                    <div class="completion-banner" id="banner_${{idx}}">
                        ✓ Module Completed!
                    </div>

                    <div class="module-header">
                        <h2>${{topic.title}}</h2>
                    </div>
                `;

                if (topic.learning_objectives && topic.learning_objectives.length > 0) {{
                    content += `
                        <div class="learning-objectives">
                            <h3>Learning Objectives for This Module</h3>
                            <ul>
                                ${{topic.learning_objectives.map(obj => `<li>${{obj}}</li>`).join('')}}
                            </ul>
                        </div>
                    `;
                }}

                content += `
                    <div class="content-body">
                        ${{topic.content || 'No content provided'}}
                    </div>
                `;

                if (topic.quiz && topic.quiz.length > 0) {{
                    content += '<div class="quiz-section"><h3>Assessment</h3>';
                    topic.quiz.forEach((q, qIdx) => {{
                        const qId = `q_${{idx}}_${{qIdx}}`;
                        content += `
                            <div class="quiz-question" id="qc_${{qId}}">
                                <div class="question-text">${{q.question}}</div>
                                <div class="quiz-options">
                        `;
                        q.options.forEach((opt, optIdx) => {{
                            content += `
                                <div class="quiz-option">
                                    <input type="radio" id="${{qId}}_${{optIdx}}" name="${{qId}}" value="${{optIdx}}" onchange="checkAnswer('${{qId}}', ${{optIdx}}, ${{q.correct}})">
                                    <label for="${{qId}}_${{optIdx}}">${{opt}}</label>
                                </div>
                            `;
                        }});
                        content += `
                                </div>
                                <div class="quiz-feedback" id="fb_${{qId}}"></div>
                            </div>
                        `;
                    }});
                    content += '</div>';
                    allAnswered[idx] = topic.quiz.length;
                }} else {{
                    completedModules[idx] = true;
                }}

                content += `
                    <div class="navigation">
                        <button class="nav-button" onclick="previousModule()" ${{idx === 0 ? 'disabled' : ''}}>
                            ← Previous
                        </button>
                        <button class="nav-button" onclick="nextModule()" ${{idx === TOPICS.length - 1 ? 'disabled' : ''}}>
                            Next →
                        </button>
                    </div>
                `;

                moduleDiv.innerHTML = content;
                modulesContainer.appendChild(moduleDiv);
            }});

            document.getElementById('modulesTotal').textContent = TOPICS.length;
            updateProgress();
        }}

        function startCourse() {{
            console.log('Start Course clicked. TOPICS:', TOPICS);
            if (!TOPICS || !Array.isArray(TOPICS) || TOPICS.length === 0) {{
                console.error('No topics available:', TOPICS);
                alert('No modules available yet. The course needs at least one module to start. Please ensure Phase 3 (pathway nodes) is complete.');
                return;
            }}
            console.log('Starting course with', TOPICS.length, 'modules');
            document.getElementById('courseIntro').classList.remove('active');
            switchModule(0);
        }}

        function switchModule(idx) {{
            if (idx < 0 || idx >= TOPICS.length) return;

            // Hide all modules
            document.querySelectorAll('[id^="module_"]').forEach(m => {{
                m.classList.remove('active');
            }});
            document.getElementById('courseIntro').classList.remove('active');
            document.getElementById('certificateSection').classList.remove('active');

            // Show selected module
            document.getElementById(`module_${{idx}}`).classList.add('active');
            currentModuleIdx = idx;

            // Update sidebar
            document.querySelectorAll('.module-item').forEach((item, i) => {{
                item.classList.toggle('active', i === idx);
            }});

            // Update breadcrumb
            document.getElementById('breadcrumbTitle').textContent = `Module ${{idx + 1}}: ${{TOPICS[idx].title}}`;

            window.scrollTo(0, 0);
        }}

        function nextModule() {{
            if (currentModuleIdx < TOPICS.length - 1) {{
                switchModule(currentModuleIdx + 1);
            }}
        }}

        function previousModule() {{
            if (currentModuleIdx > 0) {{
                switchModule(currentModuleIdx - 1);
            }}
        }}

        function checkAnswer(qId, selectedIdx, correctIdx) {{
            const feedback = document.getElementById(`fb_${{qId}}`);
            const questionContainer = document.getElementById(`qc_${{qId}}`);
            
            feedback.classList.add('show');
            questionContainer.classList.add('answered');

            if (selectedIdx === correctIdx) {{
                feedback.classList.add('correct');
                feedback.classList.remove('incorrect');
                feedback.innerHTML = '<strong>✓ Correct!</strong> Excellent work.';
                
                // Mark module as complete
                const modIdx = parseInt(qId.split('_')[1]);
                completedModules[modIdx] = true;
            }} else {{
                feedback.classList.add('incorrect');
                feedback.classList.remove('correct');
                feedback.innerHTML = '<strong>✗ Incorrect.</strong> Please review the material and try again.';
            }}

            updateProgress();
        }}

        function updateProgress() {{
            const completed = Object.keys(completedModules).length;
            const total = TOPICS.length;
            const percent = Math.round((completed / total) * 100);

            document.getElementById('progressFill').style.width = percent + '%';
            document.getElementById('progressPercent').textContent = percent + '%';
            document.getElementById('modulesCompleted').textContent = completed;

            // Update module status in sidebar
            TOPICS.forEach((_, idx) => {{
                const statusEl = document.getElementById(`status_${{idx}}`);
                if (completedModules[idx]) {{
                    statusEl.classList.add('completed');
                    statusEl.textContent = '✓';
                }} else {{
                    statusEl.classList.remove('completed');
                    statusEl.textContent = idx + 1;
                }}

                // Show completion banner
                if (completedModules[idx] && currentModuleIdx === idx) {{
                    document.getElementById(`banner_${{idx}}`).classList.add('show');
                }}
            }});

            // Show certificate if all complete
            if (completed === total) {{
                setTimeout(() => {{
                    showCertificate();
                }}, 300);
            }}
        }}

        function showCertificate() {{
            document.getElementById('certificateSection').classList.add('active');
            document.getElementById('completionDate').textContent = new Date().toLocaleDateString('en-US', {{
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            }});
            document.getElementById('recipientName').focus();
            window.scrollTo(0, 0);
        }}

        function generateCertificateID() {{
            const id = 'CPQ-' + 
                       CONDITION.substring(0, 3).toUpperCase() + '-' +
                       Date.now().toString(36).toUpperCase().substring(0, 8) +
                       '-' +
                       Math.random().toString(36).substr(2, 9).toUpperCase();
            document.getElementById('certId').textContent = id;
        }}

        function printCertificate() {{
            window.print();
        }}

        function downloadCertificateSVG() {{
            const certContent = document.querySelector('.certificate-content');
            const certId = document.getElementById('certId').textContent;
            const recipientName = document.getElementById('recipientName').value || 'Recipient';
            const svgString = new XMLSerializer().serializeToString(certContent);
            
            // Wrap in SVG for proper export
            const svgWrapper = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600" width="800" height="600">
  <defs>
    <style>
            ${{Array.from(document.styleSheets).map(sheet => {{
                try {{ return Array.from(sheet.cssRules || []).map(rule => rule.cssText).join('\n'); }}
                catch {{ return ''; }}
            }}).join('\n')}}
    </style>
  </defs>
    <foreignObject width="800" height="600" x="0" y="0">
        <div xmlns="http://www.w3.org/1999/xhtml">${{certContent.innerHTML}}</div>
    </foreignObject>
</svg>`;
            
            const blob = new Blob([svgWrapper], {{ type: 'image/svg+xml' }});
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = 'Certificate_' + recipientName.replace(/\s+/g, '_') + '_' + certId + '.svg';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
        }}

        function emailCertificate() {{
            const name = document.getElementById('recipientName').value;
            const certId = document.getElementById('certId').textContent;
            const mailto = `mailto:?subject=Education Certificate: ${{CONDITION}}&body=Your certificate ID is: ${{certId}}`;
            window.open(mailto);
        }}
    </script>
</body>
</html>"""
    
    return html
