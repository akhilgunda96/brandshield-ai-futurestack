import json
import sqlite3
from collections import Counter
from io import BytesIO

import streamlit as st

from engine import apply_suggestion
from store import Store, ROLES
from brands import BRAND_SAMPLES

from theme import (
    inject_styles,
    brand,
    hero,
    section,
    recent_reviews,
    evidence,
    status_badge,
    showcase,
    dashboard_header,
    stats,
    findings_panel,
    brands_panel,
)

st.set_page_config(page_title='BrandShield AI', page_icon='🛡️', layout='wide')
inject_styles()
db = Store()


def run_action(action, *args):
    try:
        result = action(*args)
        st.session_state['flash'] = 'Saved successfully.'
        return result, True
    except (ValueError, PermissionError, sqlite3.IntegrityError) as exc:
        st.error(str(exc))
        return None, False


brand()
if not db.has_users():
    st.subheader('Create your administrator account')
    st.write('First run setup. This account manages users and brand profiles.')
    with st.form('setup'):
        password = st.text_input(
            'Administrator password (12+ characters)', type='password'
        )
        if st.form_submit_button('Create admin', type='primary'):
            _, succeeded = run_action(db.bootstrap, password)
            if succeeded:
                st.rerun()
    st.stop()
if 'user' not in st.session_state:
    intro, signin = st.columns([1.4, 1], gap='large')
    with intro:
        showcase()
        section('A clearer path to better content')
        st.write('01  —  Choose your brand’s approved guidance')
        st.write('02  —  Review findings and refine your draft')
        st.write('03  —  Get a separate reviewer’s approval')
    with signin:
        st.subheader('Your workspace awaits.')
        st.caption('Sign in to keep your brand moving forward.')
        with st.form('login'):
            username = st.text_input('Username', placeholder='Enter your username')
            password = st.text_input(
                'Password', type='password', placeholder='Enter your password'
            )
            if st.form_submit_button(
                'Sign in', type='primary', use_container_width=True
            ):
                user = db.authenticate(username, password)
                if user:
                    st.session_state['user'] = user
                    st.rerun()
                else:
                    st.error('Invalid username or password.')
    st.stop()
current_user = st.session_state['user']
actor = current_user['username']
with st.sidebar:
    st.markdown(
        '<div class="bs-side-name">BrandShield AI</div><div class="bs-side-label">BRAND GOVERNANCE WORKSPACE</div>',
        unsafe_allow_html=True,
    )
    st.write(current_user['name'])
    st.caption(current_user['role'].upper())
    choices = ['Overview', 'Reviews']
    if current_user['role'] in ('creator', 'admin'):
        choices.append('New review')
    choices.append('Brand profiles')
    if current_user['role'] == 'admin':
        choices.append('Users')
    page = st.radio('Workspace', choices, key='workspace_page')
    st.divider()
    st.caption('Rule-based MVP · No external AI processing')
    if st.button('Sign out'):
        st.session_state.clear()
        st.rerun()
if st.session_state.pop('flash', None):
    st.success('Saved successfully.')
reviews = db.list_reviews(actor)
if page == 'Overview':
    dashboard_header(current_user['name'])
    stats(reviews)

    def navigate(target):
        st.session_state['workspace_page'] = target

    activity, insights = st.columns([1.5, 1], gap='large')
    with activity:
        section('Review workspace', 'Your latest drafts and decisions')
        actions = st.columns(2)
        if current_user['role'] in ('creator', 'admin'):
            actions[0].button(
                '＋ Start a review',
                type='primary',
                use_container_width=True,
                on_click=navigate,
                args=('New review',),
            )
        else:
            actions[0].button(
                'Open review queue →',
                type='primary',
                use_container_width=True,
                on_click=navigate,
                args=('Reviews',),
            )
        actions[1].button(
            'Browse brand profiles',
            use_container_width=True,
            on_click=navigate,
            args=('Brand profiles',),
        )
        recent_reviews(reviews)
    with insights:
        section('At a glance', 'Guidance & review patterns')
        counts = Counter()
        dismissed = Counter()
        for review in reviews:
            findings = db.detail(actor, review['id'])['revisions'][0]['findings']
            counts.update(finding['type'] for finding in findings)
            dismissed.update(
                finding['type']
                for finding in findings
                if finding['status'] == 'Dismissed'
            )
        findings_panel(counts, dismissed)
        profiles = db.profiles()
        brands_panel(
            [{**profile, 'body': json.loads(profile['body'])} for profile in profiles]
        )
        st.caption(
            'Patterns use latest revisions of visible reviews, not measured accuracy or time savings.'
        )
elif page == 'New review':
    hero(
        'CREATE / CHECK / REFINE',
        'Make every message on-brand.',
        'Choose a brand profile, add your draft, and turn configured guidance into clear, actionable findings.',
    )
    section('Prepare your draft', 'Select your approved guidance and content')
    profiles = db.profiles()
    profile = st.selectbox(
        'Brand profile',
        profiles,
        format_func=lambda profile: f"{profile['name']} · v{profile['version']}",
    )
    title = st.text_input(
        'Review title', max_chars=180, placeholder='October energy campaign'
    )
    st.selectbox(
        'Content channel', ['Social post', 'Advertisement', 'Landing page', 'Other']
    )
    st.caption(
        'Channel is descriptive context. The configured checks are the same across channels.'
    )
    upload = st.file_uploader(
        'Import a .txt, .md or text-based .pdf file', type=['txt', 'md', 'pdf']
    )
    if upload and st.button('Import text'):
        try:
            if upload.size > 5 * 1024 * 1024:
                raise ValueError('Upload limit: 5 MB.')
            if upload.name.lower().endswith('.pdf'):
                from pypdf import PdfReader

                reader = PdfReader(BytesIO(upload.getvalue()))
                if len(reader.pages) > 50:
                    raise ValueError('PDF limit: 50 pages.')
                text = '\n'.join(
                    pdf_page.extract_text() or '' for pdf_page in reader.pages
                )
            else:
                text = upload.getvalue().decode('utf-8-sig')
            if not text.strip():
                raise ValueError(
                    'No extractable text. Scanned PDFs need OCR, which is outside this MVP.'
                )
            if len(text) > 50000:
                raise ValueError('Content exceeds 50,000 characters.')
            st.session_state['new_content'] = text
            st.rerun()
        except Exception as exc:
            st.error(f'Import failed: {exc}')
    if profile['name'] in BRAND_SAMPLES and st.button('Load fictional example'):
        st.session_state['new_content'] = BRAND_SAMPLES[profile['name']]
        st.rerun()
    text = st.text_area('Content', key='new_content', height=230, max_chars=50000)
    if st.button('Analyse & save draft', type='primary'):
        review_id, succeeded = run_action(db.create, actor, title, text, profile['id'])
        if succeeded:
            st.session_state['selected_review'] = review_id
            st.success(
                f'Review #{review_id} created. Open Reviews to inspect the findings.'
            )
elif page == 'Reviews':
    section('Content reviews', 'From first draft to final decision')
    status = st.selectbox(
        'Filter status',
        ['All', 'Draft', 'Pending review', 'Changes requested', 'Approved'],
    )
    shown = [
        review for review in reviews if status == 'All' or review['status'] == status
    ]
    if not shown:
        st.info('No reviews match this filter.')
        st.stop()
    ids = [review['id'] for review in shown]
    preferred = st.session_state.get('selected_review', ids[0])
    review_id = st.selectbox(
        'Select review',
        ids,
        index=ids.index(preferred) if preferred in ids else 0,
        format_func=lambda id: next(
            f"#{id} · {review['title']} · {review['status']}"
            for review in shown
            if review['id'] == id
        ),
    )
    review = db.detail(actor, review_id)
    latest_revision = review['revisions'][0]
    st.subheader(review['title'])
    st.markdown(status_badge(review['status']), unsafe_allow_html=True)
    st.caption(
        f"{review['status']} · Revision {review['version']} · Created by {review['creator']} · {latest_revision['profile']['name']}"
    )
    editable = review['creator'] == actor and review['status'] in (
        'Draft',
        'Changes requested',
    )
    content_tab, decisions_tab, history_tab = st.tabs(
        ['Content & findings', 'Comments & decisions', 'Revision history']
    )
    with content_tab:
        left, right = st.columns([1.1, 1])
        with left:
            content = st.text_area(
                'Current content',
                latest_revision['content'],
                height=350,
                disabled=not editable,
                key=f"edit_{review_id}_{review['version']}",
            )
            st.caption(
                'Apply a focused correction or edit here, then save to run all checks again. New revisions reset finding decisions.'
            )
            if editable and st.button('Save revision & reanalyse', type='primary'):
                _, succeeded = run_action(
                    db.revise, actor, review_id, content, review['version']
                )
                if succeeded:
                    st.rerun()
            st.download_button(
                'Download review report',
                json.dumps(review, indent=2),
                file_name=f'brandshield-review-{review_id}.json',
                mime='application/json',
            )
        with right:
            open_findings = [
                finding
                for finding in latest_revision['findings']
                if finding['status'] == 'Open'
            ]
            st.write(
                f"**{len(open_findings)} open findings** · {len(latest_revision['findings'])} total"
            )
            st.caption(
                'Rule-based checks cover configured terms, phrases, tone, and a narrow energy-savings claim pattern. A clear result is not a general compliance guarantee.'
            )
            if not latest_revision['findings']:
                st.success(
                    'No configured-rule findings. Human review is still required.'
                )
            for finding in latest_revision['findings']:
                with st.expander(
                    f"{finding['severity']} · {finding['type']} · {finding['status']}",
                    expanded=finding['status'] == 'Open',
                ):
                    st.code(finding['affected'], language=None)
                    st.write(finding['explanation'])
                    st.caption(f"Source: {finding['source_id'] or 'Unverified'}")
                    evidence(finding['evidence'], finding['source_id'])
                    if finding['suggestion'] is not None:
                        st.write('Suggested replacement:')
                        st.code(finding['suggestion'], language=None)
                        if (
                            editable
                            and finding['status'] == 'Open'
                            and st.button(
                                'Apply & reanalyse', key='apply' + finding['id']
                            )
                        ):
                            if content != latest_revision['content']:
                                st.warning(
                                    'Save your unsaved edits before applying a suggestion.'
                                )
                            else:
                                try:
                                    revised = apply_suggestion(
                                        latest_revision['content'], finding
                                    )
                                    _, succeeded = run_action(
                                        db.revise,
                                        actor,
                                        review_id,
                                        revised,
                                        review['version'],
                                    )
                                    if succeeded:
                                        st.rerun()
                                except ValueError as exc:
                                    st.error(str(exc))
                    else:
                        st.caption(
                            'Manual revision required. Review the approved wording and revise the whole claim where needed.'
                        )
                    if editable:
                        note = st.text_input(
                            'Decision reason', key='reason' + finding['id']
                        )
                        decision = (
                            'Dismissed' if finding['status'] == 'Open' else 'Open'
                        )
                        if st.button(
                            (
                                'Dismiss finding'
                                if decision == 'Dismissed'
                                else 'Reopen finding'
                            ),
                            key='decision' + finding['id'],
                        ):
                            _, succeeded = run_action(
                                db.finding_decision,
                                actor,
                                review_id,
                                finding['id'],
                                decision,
                                note,
                                review['version'],
                            )
                            if succeeded:
                                st.rerun()
    with decisions_tab:
        st.subheader('Human approval')
        st.caption(
            'Open findings remain visible to the reviewer. Approval is an explicit human decision, and self-approval is blocked.'
        )
        note = st.text_area(
            'Comment or decision explanation', max_chars=5000, key=f'note{review_id}'
        )
        if st.button('Add comment'):
            _, succeeded = run_action(db.comment, actor, review_id, note)
            if succeeded:
                st.rerun()
        if editable and st.button('Request approval', type='primary'):
            _, succeeded = run_action(
                db.transition, actor, review_id, 'Submit', note, review['version']
            )
            if succeeded:
                st.rerun()
        if (
            current_user['role'] in ('reviewer', 'manager', 'admin')
            and actor != review['creator']
            and review['status'] == 'Pending review'
        ):
            for action in ['Approve', 'Request changes']:
                if st.button(action):
                    _, succeeded = run_action(
                        db.transition, actor, review_id, action, note, review['version']
                    )
                    if succeeded:
                        st.rerun()
        for event in review['events']:
            st.write(
                f"**{event['action']}** · {event['actor']} · v{event['version']} · {event['created']} UTC"
            )
            st.text(event['note'])
    with history_tab:
        st.caption(
            'Each revision retains its own content, findings and approved-source snapshot.'
        )
        for revision in review['revisions']:
            with st.expander(
                f"Revision {revision['version']} · {revision['actor']} · {revision['created']} UTC"
            ):
                st.text(revision['content'])
                st.json(revision['findings'])
                st.json(revision['profile'])
elif page == 'Brand profiles':
    from profiles_ui import render_profiles

    render_profiles(db, current_user, run_action)
elif page == 'Users':
    section('People & permissions', 'Give each teammate the right role')
    st.write(
        'Creators access their own reviews. Reviewers and managers review across the workspace. Managers configure profiles; administrators also create users.'
    )
    with st.form('user_form', clear_on_submit=True):
        name = st.text_input('Display name')
        username = st.text_input('New username')
        role = st.selectbox('Role', ROLES)
        password = st.text_input('New password (12+ characters)', type='password')
        if st.form_submit_button('Create user', type='primary'):
            run_action(db.add_user, actor, username, name, role, password)
st.markdown(
    '<div class="bs-footer"><span>BRANDSHIELD AI · TEAM GRUMPYBOT</span><span>TechCircuit Hackathon · Evidence first. People in control.</span></div>',
    unsafe_allow_html=True,
)
