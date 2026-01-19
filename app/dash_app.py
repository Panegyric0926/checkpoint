"""
Dash Frontend Application
Provides a web-based chat interface with checkpoint management
"""
import dash
from dash import html, dcc, callback, Input, Output, State, ctx, ALL
import dash_bootstrap_components as dbc
from datetime import datetime

from app.session_manager import SessionManager


# Initialize the session manager (manages multiple agent instances)
session_manager = SessionManager(session_timeout_minutes=60)


def create_app() -> dash.Dash:
    """Create and configure the Dash application"""
    
    app = dash.Dash(
        __name__,
        external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME],
        suppress_callback_exceptions=True,
        title="AI Chat with Checkpoints"
    )
    
    app.layout = create_layout()
    register_callbacks(app)
    
    return app


def create_layout() -> html.Div:
    """Create the main application layout"""
    return html.Div([
        # Header
        dbc.Navbar(
            dbc.Container([
                dbc.NavbarBrand([
                    html.I(className="fas fa-robot me-2"),
                    "AI Chat Agent with Time Travel"
                ], className="fs-4"),
                html.Div([
                    html.I(className="fas fa-fingerprint me-2"),
                    "Session: ",
                    html.Span(id="session-id-display", className="fw-bold")
                ], className="ms-auto text-white"),
            ], fluid=True),
            color="primary",
            dark=True,
            className="mb-4"
        ),
        
        # Main content
        dbc.Container([
            dbc.Row([
                # Chat Column
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.I(className="fas fa-comments me-2"),
                            "Conversation"
                        ], className="bg-primary text-white"),
                        dbc.CardBody([
                            # Chat messages container
                            dcc.Loading(
                                id="chat-loading",
                                type="circle",
                                color="#007bff",
                                children=html.Div(
                                    id="chat-messages",
                                    className="chat-container",
                                    style={
                                        "height": "500px",
                                        "overflowY": "auto",
                                        "padding": "10px",
                                        "backgroundColor": "#f8f9fa",
                                        "borderRadius": "5px"
                                    }
                                ),
                            ),
                        ]),
                        dbc.CardFooter([
                            dbc.Row([
                                dbc.Col([
                                    dbc.Input(
                                        id="user-input",
                                        type="text",
                                        placeholder="Type your message here...",
                                        style={"height": "38px"},
                                        n_submit=0,
                                        debounce=False
                                    ),
                                ], width=7),
                                dbc.Col([
                                    dbc.Button(
                                        [
                                            dbc.Spinner(
                                                html.Span(
                                                    html.I(className="fas fa-paper-plane"),
                                                    id="send-btn-content"
                                                ),
                                                id="send-spinner",
                                                size="sm",
                                                spinner_class_name="d-none",
                                            ),
                                        ],
                                        id="send-btn",
                                        color="primary",
                                        className="w-100",
                                        style={"height": "38px"}
                                    ),
                                ], width=1),
                                dbc.Col([
                                    dbc.Tooltip(
                                        "AI already saved this state",
                                        target="save-checkpoint-btn",
                                        id="save-btn-tooltip",
                                    ),
                                    dbc.Button(
                                        [html.I(className="fas fa-save me-1"), "Save"],
                                        id="save-checkpoint-btn",
                                        color="success",
                                        className="w-100",
                                        style={"height": "38px"}
                                    ),
                                ], width=2),
                                dbc.Col([
                                    dbc.Button(
                                        [html.I(className="fas fa-trash me-1"), "Clear"],
                                        id="clear-chat-btn",
                                        color="danger",
                                        outline=True,
                                        className="w-100",
                                        style={"height": "38px"}
                                    ),
                                ], width=2),
                            ]),
                        ]),
                    ], className="shadow-sm"),
                ], width=8),
                
                # Checkpoint Column
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.I(className="fas fa-clock-rotate-left me-2"),
                            "Checkpoints (Time Travel)"
                        ], className="bg-success text-white"),
                        dbc.CardBody([
                            html.P(
                                "Save conversation states and travel back in time. "
                                "Restoring a checkpoint will discard all future messages.",
                                className="text-muted small"
                            ),
                            html.Hr(),
                            html.Div(
                                id="checkpoint-list",
                                style={
                                    "height": "480px",
                                    "overflowY": "auto"
                                }
                            ),
                        ]),
                    ], className="shadow-sm"),
                ], width=4),
            ]),
            
            # Save Checkpoint Modal
            dbc.Modal([
                dbc.ModalHeader(dbc.ModalTitle("Save Checkpoint")),
                dbc.ModalBody([
                    dbc.Label("Checkpoint Name"),
                    dbc.Input(id="modal-checkpoint-name", placeholder="Enter name..."),
                    html.Br(),
                    dbc.Label("Description (optional)"),
                    dbc.Textarea(id="modal-checkpoint-desc", placeholder="What happened at this point?"),
                ]),
                dbc.ModalFooter([
                    dbc.Button("Cancel", id="modal-cancel-btn", color="secondary"),
                    dbc.Button("Save", id="modal-save-btn", color="success"),
                ]),
            ], id="save-checkpoint-modal", is_open=False),
            
            # Confirm Restore Modal
            dbc.Modal([
                dbc.ModalHeader(dbc.ModalTitle("Confirm Time Travel")),
                dbc.ModalBody([
                    html.P([
                        html.I(className="fas fa-exclamation-triangle text-warning me-2"),
                        "Are you sure you want to restore to this checkpoint?"
                    ]),
                    html.P(
                        "All messages after this checkpoint will be removed.",
                        className="text-danger"
                    ),
                    html.Div(id="restore-checkpoint-info"),
                ]),
                dbc.ModalFooter([
                    dbc.Button("Cancel", id="restore-cancel-btn", color="secondary"),
                    dbc.Button("Restore", id="restore-confirm-btn", color="danger"),
                ]),
            ], id="restore-checkpoint-modal", is_open=False),
            
            # Hidden stores for state management
            dcc.Store(id="session-id", storage_type="session"),  # Store session ID (persists within tab)
            dcc.Store(id="pending-restore-checkpoint-id"),
            dcc.Store(id="chat-trigger", data=0),
            dcc.Store(id="checkpoint-trigger", data=0),
            dcc.Store(id="pending-message", data=""),  # Store for pending message
            dcc.Store(id="has-unsaved-changes", data=False),  # Track if there are unsaved changes
            dcc.Store(id="ai-checkpoint-exists", data=False),  # Track if AI created checkpoint for current state
            dcc.Store(id="editing-message-index", data=None),  # Track which message is being edited (in the message box)
            dcc.Store(id="pending-edit-data", data=None),  # Store edited content for processing
            
            # Dummy location component to trigger initial callbacks
            dcc.Location(id="url", refresh=False)
            
        ], fluid=True),
        
        # Footer
        html.Footer([
            html.Hr(),
            html.P([
                "Powered by LangGraph | ",
                "Traced with Langfuse"
            ], className="text-center text-muted small"),
        ], className="mt-4 mb-3"),
        
        # Custom CSS injection using dcc.Markdown with style tag
        dcc.Markdown("""
<style>
.chat-message {
    padding: 12px 16px;
    margin: 8px 0;
    border-radius: 12px;
    max-width: 75%;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    word-wrap: break-word;
}
.user-message {
    background: linear-gradient(135deg, #4a90d9 0%, #2563eb 100%) !important;
    color: white !important;
    border-bottom-right-radius: 4px;
    margin-left: auto;
}
.user-message .fw-bold {
    color: rgba(255, 255, 255, 0.9) !important;
}
.assistant-message {
    background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%) !important;
    border: 1px solid #a5d6a7 !important;
    color: #1b5e20 !important;
    border-bottom-left-radius: 4px;
}
.assistant-message .fw-bold {
    color: #2e7d32 !important;
}
.assistant-message p {
    margin-bottom: 0.5rem;
    color: #1b5e20 !important;
}
.checkpoint-item {
    padding: 10px;
    margin: 5px 0;
    border-radius: 8px;
    background-color: #f8f9fa;
    cursor: pointer;
    transition: all 0.2s;
}
.checkpoint-item:hover {
    background-color: #e9ecef;
    transform: translateX(3px);
}
</style>
""", dangerously_allow_html=True),
    ])


def register_callbacks(app: dash.Dash) -> None:
    """Register all Dash callbacks"""
    
    @app.callback(
        Output("session-id", "data"),
        Output("session-id-display", "children"),
        Input("url", "pathname"),
        State("session-id", "data"),
    )
    def initialize_session(pathname, session_id):
        """Initialize or retrieve session ID for this browser tab"""
        if not session_id:
            # Create new session for this tab
            new_session_id = session_manager.create_session()
            return new_session_id, new_session_id
        else:
            # Verify existing session is still valid
            agent = session_manager.get_agent(session_id)
            if not agent:
                # Session expired, create new one
                new_session_id = session_manager.create_session()
                return new_session_id, new_session_id
            
            # Session is valid
            return session_id, session_id
    
    @app.callback(
        Output("chat-messages", "children"),
        Input("chat-trigger", "data"),
        Input("session-id", "data"),
        Input("editing-message-index", "data"),
    )
    def update_chat_display(_, session_id, editing_index):
        """Update the chat display with current conversation"""
        if not session_id:
            return html.Div([
                html.I(className="fas fa-spinner fa-spin fa-3x text-primary"),
                html.P("Initializing session...", className="text-muted mt-2")
            ], className="text-center py-5")
        
        agent = session_manager.get_agent(session_id)
        if not agent:
            return html.Div([
                html.I(className="fas fa-exclamation-triangle fa-3x text-danger"),
                html.P("Session expired. Please refresh the page.", className="text-muted mt-2")
            ], className="text-center py-5")
        
        history = agent.get_conversation_with_edit_info()
        
        if not history:
            return html.Div([
                html.I(className="fas fa-comments fa-3x text-muted"),
                html.P("Start a conversation!", className="text-muted mt-2")
            ], className="text-center py-5")
        
        messages = []
        for idx, msg in enumerate(history):
            role = msg["role"]
            content = msg["content"]
            has_edits = msg["has_edits"]
            edit_versions = msg["edit_versions"]
            current_version_idx = msg["current_version_index"]
            
            if role == "user":
                # Find the last user message index
                last_user_idx = -1
                for i in range(len(history) - 1, -1, -1):
                    if history[i]["role"] == "user":
                        last_user_idx = i
                        break
                
                # Only show edit button and version navigation for the last user message
                is_last_user_message = (idx == last_user_idx)
                
                # Build version navigation if there are edits AND this is the last user message
                version_nav = None
                if is_last_user_message and has_edits and len(edit_versions) > 1:
                    version_nav = html.Div([
                        dbc.Button(
                            html.I(className="fas fa-chevron-left"),
                            id={"type": "prev-version-btn", "index": idx},
                            size="sm",
                            color="light",
                            outline=True,
                            disabled=(current_version_idx <= 0),
                            className="me-1",
                            style={"padding": "2px 6px", "fontSize": "0.7rem"}
                        ),
                        html.Span(
                            f"{current_version_idx + 1}/{len(edit_versions)}",
                            className="text-white small me-1",
                            style={"fontSize": "0.75rem", "opacity": "0.8"}
                        ),
                        dbc.Button(
                            html.I(className="fas fa-chevron-right"),
                            id={"type": "next-version-btn", "index": idx},
                            size="sm",
                            color="light",
                            outline=True,
                            disabled=(current_version_idx >= len(edit_versions) - 1),
                            className="me-2",
                            style={"padding": "2px 6px", "fontSize": "0.7rem"}
                        ),
                    ], className="d-inline-flex align-items-center mt-2")
                
                # Check if this message is being edited
                is_editing = (editing_index == idx)
                
                if is_editing:
                    # Show editable textarea with save/cancel buttons
                    messages.append(html.Div([
                        html.Div([
                            html.Div([html.I(className="fas fa-user me-1"), "You"], className="fw-bold mb-1"),
                            dbc.Textarea(
                                id={"type": "edit-textarea", "index": idx},
                                value=content,
                                style={"minHeight": "80px", "backgroundColor": "rgba(255,255,255,0.95)", "color": "#333"},
                                className="mb-2"
                            ),
                            html.Div([
                                dbc.Button(
                                    [html.I(className="fas fa-check me-1"), "Update"],
                                    id={"type": "save-edit-btn", "index": idx},
                                    size="sm",
                                    color="success",
                                    className="me-2"
                                ),
                                dbc.Button(
                                    [html.I(className="fas fa-times me-1"), "Cancel"],
                                    id={"type": "cancel-edit-btn", "index": idx},
                                    size="sm",
                                    color="secondary",
                                    outline=True
                                )
                            ])
                        ], className="chat-message user-message", style={
                            "padding": "12px 16px",
                            "margin": "8px 0",
                            "borderRadius": "12px",
                            "maxWidth": "75%",
                            "boxShadow": "0 2px 4px rgba(0,0,0,0.1)",
                            "background": "linear-gradient(135deg, #4a90d9 0%, #2563eb 100%)",
                            "color": "white",
                            "borderBottomRightRadius": "4px",
                        })
                    ], style={"display": "flex", "justifyContent": "flex-end"}))
                else:
                    # Show normal message with edit button
                    messages.append(html.Div([
                        html.Div([
                            html.Div([html.I(className="fas fa-user me-1"), "You"], className="fw-bold mb-1"),
                            html.Div(content),
                            html.Div([
                                version_nav if version_nav else html.Span(),
                                dbc.Button(
                                    html.I(className="fas fa-edit"),
                                    id={"type": "edit-msg-btn", "index": idx},
                                    size="sm",
                                    color="light",
                                    outline=True,
                                    className="mt-2",
                                    title="Edit and create new branch",
                                    style={"opacity": "0.7", "display": "inline-block" if is_last_user_message else "none"}
                                )
                            ], className="d-flex justify-content-between align-items-center")
                        ], className="chat-message user-message", style={
                            "padding": "12px 16px",
                            "margin": "8px 0",
                            "borderRadius": "12px",
                            "maxWidth": "75%",
                            "boxShadow": "0 2px 4px rgba(0,0,0,0.1)",
                            "background": "linear-gradient(135deg, #4a90d9 0%, #2563eb 100%)",
                            "color": "white",
                            "borderBottomRightRadius": "4px",
                        })
                    ], style={"display": "flex", "justifyContent": "flex-end"}))
            else:
                messages.append(html.Div([
                    html.Div([
                        html.Div([html.I(className="fas fa-robot me-1"), "Assistant"], 
                                 className="fw-bold mb-1", style={"color": "#2e7d32"}),
                        dcc.Markdown(content, style={"color": "#1b5e20"})
                    ], className="chat-message assistant-message", style={
                        "padding": "12px 16px",
                        "margin": "8px 0",
                        "borderRadius": "12px",
                        "maxWidth": "75%",
                        "boxShadow": "0 2px 4px rgba(0,0,0,0.1)",
                        "background": "linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%)",
                        "border": "1px solid #a5d6a7",
                        "color": "#1b5e20",
                        "borderBottomLeftRadius": "4px",
                    })
                ], style={"display": "flex", "justifyContent": "flex-start"}))
        
        return messages
    
    @app.callback(
        Output("send-btn", "disabled"),
        Output("user-input", "disabled"),
        Output("send-btn", "color"),
        Output("send-spinner", "spinner_class_name"),
        Output("send-btn-content", "children"),
        Input("pending-message", "data"),
        Input("pending-edit-data", "data"),
        Input("chat-trigger", "data"),
    )
    def toggle_input_state(pending_message, pending_edit, chat_trigger):
        """Disable input while processing and show loading state"""
        triggered_id = ctx.triggered_id
        
        btn_content = html.I(className="fas fa-paper-plane")
        
        # If message or edit is being processed, disable inputs and show loading
        if (triggered_id == "pending-message" and pending_message) or (triggered_id == "pending-edit-data" and pending_edit):
            return True, True, "secondary", "", btn_content
        
        # Normal state: inputs enabled
        return False, False, "primary", "d-none", btn_content
    
    @app.callback(
        Output("save-checkpoint-btn", "disabled"),
        Output("save-checkpoint-btn", "color"),
        Output("save-btn-tooltip", "children"),
        Input("has-unsaved-changes", "data"),
        Input("ai-checkpoint-exists", "data"),
    )
    def toggle_save_button(has_unsaved_changes, ai_checkpoint_exists):
        """Enable/disable save button based on whether there are unsaved changes and AI checkpoint status"""
        if ai_checkpoint_exists:
            # AI already saved - disable and show grey with tooltip
            return True, "secondary", "AI already saved this state"
        elif has_unsaved_changes:
            # Changes exist and no AI checkpoint - enable green button
            return False, "success", "Save checkpoint"
        else:
            # No unsaved changes - disable grey button
            return True, "secondary", "No unsaved changes"
    
    @app.callback(
        Output("checkpoint-list", "children"),
        Input("checkpoint-trigger", "data"),
        Input("session-id", "data"),
    )
    def update_checkpoint_list(_, session_id):
        """Update the checkpoint list display"""
        if not session_id:
            return html.Div([
                html.I(className="fas fa-spinner fa-spin text-muted"),
                html.P("Initializing...", className="text-muted small text-center mt-2")
            ], className="text-center py-4")
        
        agent = session_manager.get_agent(session_id)
        if not agent:
            return html.Div([
                html.P("Session expired", className="text-danger small text-center")
            ])
        
        checkpoints = agent.list_checkpoints()
        
        if not checkpoints:
            return html.Div([
                html.I(className="fas fa-clock fa-2x text-muted"),
                html.P("No checkpoints saved yet", className="text-muted mt-2 small")
            ], className="text-center py-4")
        
        items = []
        for cp in reversed(checkpoints):  # Show newest first
            timestamp = datetime.fromisoformat(cp["timestamp"]).strftime("%H:%M:%S")
            
            # Determine styling based on creator
            created_by = cp.get("created_by", "human")
            if created_by == "ai":
                border_color = "#17a2b8"  # Info blue for AI
                icon_class = "fas fa-robot"
                creator_badge = dbc.Badge("AI", color="info", className="ms-2")
            else:
                border_color = "#28a745"  # Green for human
                icon_class = "fas fa-user"
                creator_badge = dbc.Badge("Manual", color="success", className="ms-2")
            
            items.append(
                html.Div([
                    html.Div([
                        html.I(className=f"{icon_class} me-1", style={"fontSize": "0.9rem"}),
                        html.Strong(cp["name"]),
                        creator_badge,
                        html.Span(f" ({cp['message_count']} msgs)", className="text-muted small"),
                    ]),
                    html.Small([
                        html.I(className="fas fa-clock me-1"),
                        timestamp
                    ], className="text-muted"),
                    html.Div([
                        dbc.Button(
                            html.I(className="fas fa-undo"),
                            id={"type": "restore-btn", "index": cp["id"]},
                            size="sm",
                            color="warning",
                            className="me-1",
                            title="Restore to this checkpoint"
                        ),
                        dbc.Button(
                            html.I(className="fas fa-trash"),
                            id={"type": "delete-btn", "index": cp["id"]},
                            size="sm",
                            color="danger",
                            outline=True,
                            title="Delete checkpoint"
                        ),
                    ], className="mt-2"),
                    html.Small(cp.get("description", ""), className="text-muted d-block mt-1")
                    if cp.get("description") else None,
                ], 
                className="checkpoint-item", 
                style={"borderLeft": f"3px solid {border_color}"},
                id={"type": "checkpoint-item", "index": cp["id"]})
            )
        
        return items
    
    @app.callback(
        Output("pending-edit-data", "data"),
        Output("editing-message-index", "data", allow_duplicate=True),
        Input({"type": "save-edit-btn", "index": ALL}, "n_clicks"),
        State({"type": "edit-textarea", "index": ALL}, "value"),
        prevent_initial_call=True
    )
    def handle_save_edit(save_clicks, textarea_values):
        """Capture edited content when save button is clicked"""
        triggered_id = ctx.triggered_id
        
        if isinstance(triggered_id, dict) and triggered_id.get("type") == "save-edit-btn":
            if any(click is not None and click > 0 for click in save_clicks):
                message_index = triggered_id["index"]
                # Find the corresponding textarea value
                if textarea_values and len(textarea_values) > 0:
                    edited_content = textarea_values[0]  # There should only be one textarea active
                    if edited_content and edited_content.strip():
                        return {"index": message_index, "content": edited_content.strip()}, None
        
        return dash.no_update, dash.no_update
    
    @app.callback(
        Output("user-input", "value", allow_duplicate=True),
        Output("pending-message", "data"),
        Input("send-btn", "n_clicks"),
        Input("user-input", "n_submit"),
        State("user-input", "value"),
        prevent_initial_call=True
    )
    def capture_and_clear_input(n_clicks, n_submit, user_input):
        """Immediately clear input and store the message for processing"""
        if not user_input or not user_input.strip():
            return dash.no_update, dash.no_update
        
        # Store new message for processing
        return "", {"type": "new", "content": user_input.strip()}
    
    @app.callback(
        Output("chat-trigger", "data", allow_duplicate=True),
        Output("has-unsaved-changes", "data", allow_duplicate=True),
        Output("checkpoint-trigger", "data", allow_duplicate=True),
        Output("ai-checkpoint-exists", "data", allow_duplicate=True),
        Input("pending-message", "data"),
        Input("pending-edit-data", "data"),
        State("chat-trigger", "data"),
        State("checkpoint-trigger", "data"),
        State("session-id", "data"),
        prevent_initial_call=True
    )
    def process_message(message_data, edit_data, chat_trigger, cp_trigger, session_id):
        """Process either a new message or an edited message"""
        if not session_id:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        agent = session_manager.get_agent(session_id)
        if not agent:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        triggered_id = ctx.triggered_id
        
        # Handle edit message (from message box)
        if triggered_id == "pending-edit-data" and edit_data:
            message_index = edit_data.get("index")
            content = edit_data.get("content")
            if message_index is not None and content:
                agent.edit_message(message_index, content)
                # After editing, the old AI checkpoint no longer matches the edited content
                # Mark as unsaved and disable ai-checkpoint-exists
                return (chat_trigger or 0) + 1, True, cp_trigger, False
        # Handle new message (from input line)
        elif triggered_id == "pending-message" and message_data:
            msg_type = message_data.get("type")
            content = message_data.get("content")
            if msg_type == "new" and content:
                agent.chat(content)
            else:
                return dash.no_update, dash.no_update, dash.no_update, dash.no_update
        else:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        # Check if AI created a checkpoint for this state (only for new messages)
        ai_checkpoint_exists = agent.has_auto_checkpoint_for_current_state()
        
        # If AI saved, no unsaved changes; otherwise mark as unsaved
        has_unsaved = not ai_checkpoint_exists
        
        # Increment checkpoint trigger if AI created a checkpoint
        new_cp_trigger = (cp_trigger or 0) + 1 if ai_checkpoint_exists else cp_trigger
        
        return (chat_trigger or 0) + 1, has_unsaved, new_cp_trigger, ai_checkpoint_exists
    
    @app.callback(
        Output("save-checkpoint-modal", "is_open"),
        Input("save-checkpoint-btn", "n_clicks"),
        Input("modal-cancel-btn", "n_clicks"),
        Input("modal-save-btn", "n_clicks"),
        State("save-checkpoint-modal", "is_open"),
        prevent_initial_call=True
    )
    def toggle_save_modal(save_click, cancel_click, confirm_click, is_open):
        """Toggle the save checkpoint modal"""
        return not is_open
    
    @app.callback(
        Output("checkpoint-trigger", "data", allow_duplicate=True),
        Output("modal-checkpoint-name", "value"),
        Output("modal-checkpoint-desc", "value"),
        Output("has-unsaved-changes", "data", allow_duplicate=True),
        Output("ai-checkpoint-exists", "data", allow_duplicate=True),
        Input("modal-save-btn", "n_clicks"),
        State("modal-checkpoint-name", "value"),
        State("modal-checkpoint-desc", "value"),
        State("checkpoint-trigger", "data"),
        State("session-id", "data"),
        prevent_initial_call=True
    )
    def save_checkpoint(n_clicks, name, description, trigger, session_id):
        """Save a new checkpoint (human-initiated)"""
        if not n_clicks or not session_id:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        agent = session_manager.get_agent(session_id)
        if not agent:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        agent.save_checkpoint(name=name, description=description or "")
        
        # Mark that changes have been saved (no unsaved changes, no AI checkpoint for this exact state anymore)
        return (trigger or 0) + 1, "", "", False, False
    
    @app.callback(
        Output("restore-checkpoint-modal", "is_open"),
        Output("pending-restore-checkpoint-id", "data"),
        Output("restore-checkpoint-info", "children"),
        Input({"type": "restore-btn", "index": ALL}, "n_clicks"),
        Input("restore-cancel-btn", "n_clicks"),
        Input("restore-confirm-btn", "n_clicks"),
        State("restore-checkpoint-modal", "is_open"),
        State("pending-restore-checkpoint-id", "data"),
        State("session-id", "data"),
        prevent_initial_call=True
    )
    def handle_restore_modal(restore_clicks, cancel_click, confirm_click, is_open, pending_id, session_id):
        """Handle restore checkpoint modal"""
        triggered_id = ctx.triggered_id
        
        if triggered_id == "restore-cancel-btn" or triggered_id == "restore-confirm-btn":
            return False, None, ""
        
        if isinstance(triggered_id, dict) and triggered_id.get("type") == "restore-btn":
            # Check if the button was actually clicked (not just re-rendered)
            # Find the index of the clicked button and verify it has a click count
            if restore_clicks and any(click is not None and click > 0 for click in restore_clicks):
                if not session_id:
                    return dash.no_update, dash.no_update, dash.no_update
                
                agent = session_manager.get_agent(session_id)
                if not agent:
                    return dash.no_update, dash.no_update, dash.no_update
                
                checkpoint_id = triggered_id["index"]
                checkpoints = agent.list_checkpoints()
                cp_info = next((cp for cp in checkpoints if cp["id"] == checkpoint_id), None)
                
                if cp_info:
                    info = html.Div([
                        html.Strong(f"Checkpoint: {cp_info['name']}"),
                        html.Br(),
                        html.Small(f"Messages: {cp_info['message_count']}")
                    ])
                    return True, checkpoint_id, info
        
        return dash.no_update, dash.no_update, dash.no_update
    
    @app.callback(
        Output("chat-trigger", "data", allow_duplicate=True),
        Output("checkpoint-trigger", "data", allow_duplicate=True),
        Input("restore-confirm-btn", "n_clicks"),
        State("pending-restore-checkpoint-id", "data"),
        State("chat-trigger", "data"),
        State("checkpoint-trigger", "data"),
        State("session-id", "data"),
        prevent_initial_call=True
    )
    def confirm_restore(n_clicks, checkpoint_id, chat_trigger, cp_trigger, session_id):
        """Confirm and execute checkpoint restoration"""
        if not n_clicks or not checkpoint_id or not session_id:
            return dash.no_update, dash.no_update
        
        agent = session_manager.get_agent(session_id)
        if not agent:
            return dash.no_update, dash.no_update
        
        agent.restore_checkpoint(checkpoint_id)
        
        return (chat_trigger or 0) + 1, (cp_trigger or 0) + 1
    
    @app.callback(
        Output("checkpoint-trigger", "data", allow_duplicate=True),
        Input({"type": "delete-btn", "index": ALL}, "n_clicks"),
        State("checkpoint-trigger", "data"),
        State("session-id", "data"),
        prevent_initial_call=True
    )
    def delete_checkpoint(delete_clicks, trigger, session_id):
        """Delete a checkpoint"""
        triggered_id = ctx.triggered_id
        
        if isinstance(triggered_id, dict) and triggered_id.get("type") == "delete-btn":
            if any(delete_clicks) and session_id:
                agent = session_manager.get_agent(session_id)
                if agent:
                    checkpoint_id = triggered_id["index"]
                    agent.delete_checkpoint(checkpoint_id)
                    return (trigger or 0) + 1
        
        return dash.no_update
    
    @app.callback(
        Output("chat-trigger", "data", allow_duplicate=True),
        Output("checkpoint-trigger", "data", allow_duplicate=True),
        Output("has-unsaved-changes", "data", allow_duplicate=True),
        Output("ai-checkpoint-exists", "data", allow_duplicate=True),
        Input("clear-chat-btn", "n_clicks"),
        State("chat-trigger", "data"),
        State("checkpoint-trigger", "data"),
        State("session-id", "data"),
        prevent_initial_call=True
    )
    def clear_chat(n_clicks, chat_trigger, cp_trigger, session_id):
        """Clear the chat and all checkpoints"""
        if not n_clicks or not session_id:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        agent = session_manager.get_agent(session_id)
        if not agent:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        agent.clear_conversation()
        agent.checkpoint_manager.clear_all()
        
        # Reset all state flags (nothing to save after clearing)
        return (chat_trigger or 0) + 1, (cp_trigger or 0) + 1, False, False
    
    @app.callback(
        Output("editing-message-index", "data"),
        Input({"type": "edit-msg-btn", "index": ALL}, "n_clicks"),
        Input({"type": "cancel-edit-btn", "index": ALL}, "n_clicks"),
        prevent_initial_call=True
    )
    def handle_edit_mode(edit_clicks, cancel_clicks):
        """Toggle edit mode for a message"""
        triggered_id = ctx.triggered_id
        
        # Enter edit mode when edit button is clicked
        if isinstance(triggered_id, dict) and triggered_id.get("type") == "edit-msg-btn":
            if any(click is not None and click > 0 for click in edit_clicks):
                return triggered_id["index"]
        
        # Exit edit mode when cancel button is clicked
        if isinstance(triggered_id, dict) and triggered_id.get("type") == "cancel-edit-btn":
            if any(click is not None and click > 0 for click in cancel_clicks):
                return None
        
        return dash.no_update
    
    @app.callback(
        Output("chat-trigger", "data", allow_duplicate=True),
        Input({"type": "prev-version-btn", "index": ALL}, "n_clicks"),
        State("chat-trigger", "data"),
        State("session-id", "data"),
        prevent_initial_call=True
    )
    def switch_to_previous_version(prev_clicks, chat_trigger, session_id):
        """Switch to previous version of an edited message"""
        triggered_id = ctx.triggered_id
        
        if isinstance(triggered_id, dict) and triggered_id.get("type") == "prev-version-btn":
            if any(click is not None and click > 0 for click in prev_clicks):
                if not session_id:
                    return dash.no_update
                
                agent = session_manager.get_agent(session_id)
                if not agent:
                    return dash.no_update
                
                message_index = triggered_id["index"]
                history = agent.get_conversation_with_edit_info()
                
                if message_index < len(history):
                    msg_info = history[message_index]
                    if msg_info["has_edits"]:
                        current_version = msg_info["current_version_index"]
                        if current_version > 0:
                            agent.switch_message_version(message_index, current_version - 1)
                            return (chat_trigger or 0) + 1
        
        return dash.no_update
    
    @app.callback(
        Output("chat-trigger", "data", allow_duplicate=True),
        Input({"type": "next-version-btn", "index": ALL}, "n_clicks"),
        State("chat-trigger", "data"),
        State("session-id", "data"),
        prevent_initial_call=True
    )
    def switch_to_next_version(next_clicks, chat_trigger, session_id):
        """Switch to next version of an edited message"""
        triggered_id = ctx.triggered_id
        
        if isinstance(triggered_id, dict) and triggered_id.get("type") == "next-version-btn":
            if any(click is not None and click > 0 for click in next_clicks):
                if not session_id:
                    return dash.no_update
                
                agent = session_manager.get_agent(session_id)
                if not agent:
                    return dash.no_update
                
                message_index = triggered_id["index"]
                history = agent.get_conversation_with_edit_info()
                
                if message_index < len(history):
                    msg_info = history[message_index]
                    if msg_info["has_edits"]:
                        current_version = msg_info["current_version_index"]
                        if current_version < len(msg_info["edit_versions"]) - 1:
                            agent.switch_message_version(message_index, current_version + 1)
                            return (chat_trigger or 0) + 1
        
        return dash.no_update
    
    @app.callback(
        Output("chat-trigger", "data", allow_duplicate=True),
        Output("has-unsaved-changes", "data", allow_duplicate=True),
        Output("checkpoint-trigger", "data", allow_duplicate=True),
        Output("ai-checkpoint-exists", "data", allow_duplicate=True),
        Input("pending-edit-content", "data"),
        State("chat-trigger", "data"),
        State("checkpoint-trigger", "data"),
        State("session-id", "data"),
        prevent_initial_call=True
    )
    def process_edit(edit_data, chat_trigger, cp_trigger, session_id):
        """Process the edited message and regenerate response"""
        if not edit_data or not session_id:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        agent = session_manager.get_agent(session_id)
        if not agent:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        message_index = edit_data["index"]
        new_content = edit_data["content"]
        
        # Process the edit (this truncates messages and regenerates AI response)
        agent.edit_message(message_index, new_content)
        
        # Check if AI created a checkpoint for this state
        ai_checkpoint_exists = agent.has_auto_checkpoint_for_current_state()
        
        # If AI saved, no unsaved changes; otherwise mark as unsaved
        has_unsaved = not ai_checkpoint_exists
        
        # Increment checkpoint trigger if AI created a checkpoint
        new_cp_trigger = (cp_trigger or 0) + 1 if ai_checkpoint_exists else cp_trigger
        
        return (chat_trigger or 0) + 1, has_unsaved, new_cp_trigger, ai_checkpoint_exists
