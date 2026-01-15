"""
Sidebar container managing all tab list items.
Handles tab ordering, selection, and drag-and-drop reordering.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QFrame
from PyQt6.QtCore import Qt, QPoint

from constants import TAB_WIDTH_MINIMIZED, TAB_WIDTH_NORMAL, TAB_WIDTH_MAXIMIZED
from widgets.tab_list_item import TabListItem


class TabListWidget(QWidget):
    """Sidebar widget containing list of tabs"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tab_items = []  # List of TabListItem widgets
        self.view_mode = 'normal'  # Current view mode

        # Create main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create scroll area for tabs
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Container for tab list
        self.tab_container = QWidget()
        self.tab_layout = QVBoxLayout()
        self.tab_layout.setContentsMargins(10, 5, 10, 5)  # Add margins around tabs (left, top, right, bottom)
        self.tab_layout.setSpacing(4)  # Space between tabs
        self.tab_layout.addStretch()  # Push tabs to top
        self.tab_container.setLayout(self.tab_layout)

        # Create divider between pinned and unpinned tabs
        self.pinned_divider = QFrame()
        self.pinned_divider.setFrameShape(QFrame.Shape.NoFrame)
        self.pinned_divider.setStyleSheet("background-color: #000000; min-height: 2px; max-height: 2px;")
        self.pinned_divider.setVisible(False)  # Hidden by default

        # Create drop indicator for drag operations
        self.drop_indicator = QFrame()
        self.drop_indicator.setFrameShape(QFrame.Shape.HLine)
        self.drop_indicator.setStyleSheet("background-color: #2196F3; min-height: 3px; max-height: 3px;")
        self.drop_indicator.setVisible(False)  # Hidden by default
        self.drop_indicator_index = -1  # Track where drop indicator is

        scroll_area.setWidget(self.tab_container)
        main_layout.addWidget(scroll_area, 1)  # Stretch

        self.setLayout(main_layout)

        # Set background color for sidebar to match toolbar
        self.setStyleSheet("QWidget { background-color: #E8E8E8; }")
        scroll_area.setStyleSheet("QScrollArea { background-color: #E8E8E8; border: none; }")
        self.tab_container.setStyleSheet("QWidget { background-color: #E8E8E8; }")

        # Enable drag and drop
        self.setAcceptDrops(True)
        self.tab_container.setAcceptDrops(True)

        # Track if we've done initial geometry setup
        self._geometry_initialized = False

    def showEvent(self, event):
        """Handle widget show event to ensure geometry is initialized"""
        super().showEvent(event)
        if not self._geometry_initialized:
            self._ensure_geometry_initialized()

    def _ensure_geometry_initialized(self):
        """Force a complete geometry initialization - call this before first drag"""
        if self._geometry_initialized:
            return

        # The key insight: layout doesn't actually position items until they're queried or redrawn
        # Force a complete layout pass by temporarily removing and re-adding all items
        tab_items_copy = list(self.tab_items)

        # Remove all tabs from layout
        for tab_item in tab_items_copy:
            self.tab_layout.removeWidget(tab_item)

        # Re-add them (this forces layout calculation)
        for tab_item in tab_items_copy:
            self.tab_layout.insertWidget(self.tab_layout.count() - 1, tab_item)

        # Update divider position after layout rebuild
        self.update_pinned_divider()

        # Now force geometry update
        self.tab_container.layout().activate()
        self.tab_container.updateGeometry()
        self.updateGeometry()

        # Process all pending events
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()

        self._geometry_initialized = True

    def add_tab(self, editor_tab):
        """Add a new tab to the list"""
        tab_item = TabListItem(editor_tab, self)
        tab_item.set_view_mode(self.view_mode)

        # Connect buttons
        tab_item.save_btn.clicked.connect(lambda: self.on_save_clicked(editor_tab))
        tab_item.pin_btn.clicked.connect(lambda: self.on_pin_clicked(editor_tab))
        tab_item.close_btn.clicked.connect(lambda: self.on_close_clicked(editor_tab))

        # Insert based on pinned status
        if editor_tab.is_pinned:
            # Insert at the beginning (or after other pinned tabs)
            insert_index = 0
            for i, item in enumerate(self.tab_items):
                if not item.editor_tab.is_pinned:
                    insert_index = i
                    break
                insert_index = i + 1

            self.tab_items.insert(insert_index, tab_item)
            self.tab_layout.insertWidget(insert_index, tab_item)
        else:
            # Add to end
            self.tab_items.append(tab_item)
            # Insert before the stretch (which is always last in the layout)
            self.tab_layout.insertWidget(self.tab_layout.count() - 1, tab_item)

        self.update_pinned_divider()
        return tab_item

    def remove_tab(self, editor_tab):
        """Remove a tab from the list"""
        for i, tab_item in enumerate(self.tab_items):
            if tab_item.editor_tab == editor_tab:
                self.tab_layout.removeWidget(tab_item)
                tab_item.deleteLater()
                self.tab_items.pop(i)
                break
        self.update_pinned_divider()

    def clear_all_tabs(self):
        """Remove all tabs from the list (preserves divider and other UI elements)"""
        # Remove divider from layout first (we'll keep the object)
        if self.pinned_divider.parent():
            self.tab_layout.removeWidget(self.pinned_divider)
        self.pinned_divider.setVisible(False)

        # Remove drop indicator if visible
        if self.drop_indicator.parent():
            self.tab_layout.removeWidget(self.drop_indicator)
        self.drop_indicator.setVisible(False)

        # Delete all tab items
        for tab_item in self.tab_items:
            self.tab_layout.removeWidget(tab_item)
            tab_item.deleteLater()
        self.tab_items.clear()

    def update_pinned_divider(self):
        """Update the position and visibility of the divider between pinned and unpinned tabs"""
        # Count pinned tabs
        pinned_count = sum(1 for item in self.tab_items if item.editor_tab.is_pinned)

        # Remove divider from layout if it's already there
        if self.pinned_divider.parent():
            self.tab_layout.removeWidget(self.pinned_divider)

        # Only show divider if we have both pinned and unpinned tabs
        if pinned_count > 0 and pinned_count < len(self.tab_items):
            self.pinned_divider.setVisible(True)
            # Insert divider after the last pinned tab
            self.tab_layout.insertWidget(pinned_count, self.pinned_divider)
        else:
            self.pinned_divider.setVisible(False)

    def select_tab(self, tab_item):
        """Select a tab item"""
        # Deselect all others
        for item in self.tab_items:
            item.set_selected(False)

        # Select this one
        tab_item.set_selected(True)

        # Notify parent window
        parent = self.parent()
        while parent:
            if parent.__class__.__name__ == 'TextEditorWindow':
                parent.switch_to_tab(tab_item.editor_tab)
                break
            parent = parent.parent()

    def set_view_mode(self, mode):
        """Set view mode for all tabs"""
        self.view_mode = mode

        # Update all tab items
        for tab_item in self.tab_items:
            tab_item.set_view_mode(mode)

        # Adjust sidebar width based on mode
        parent = self.parent()
        while parent:
            if parent.__class__.__name__ == 'TextEditorWindow':
                # Get total width - use splitter if available, otherwise use window width
                total_width = parent.splitter.width()
                if total_width < 100:  # Splitter not laid out yet
                    # Use window width instead of hardcoded default
                    total_width = parent.width()
                    if total_width < 100:  # Window also not sized yet
                        total_width = 1200  # Last resort fallback

                # Set sidebar width based on mode
                if mode == 'minimized':
                    sidebar_width = TAB_WIDTH_MINIMIZED
                elif mode == 'normal':
                    sidebar_width = TAB_WIDTH_NORMAL
                else:  # maximized
                    sidebar_width = TAB_WIDTH_MAXIMIZED

                # Calculate content width (ensure it's at least 200px)
                content_width = max(200, total_width - sidebar_width)

                parent.splitter.setSizes([sidebar_width, content_width])
                break
            parent = parent.parent()

    def update_tab_display(self, editor_tab):
        """Update display for a specific tab"""
        for tab_item in self.tab_items:
            if tab_item.editor_tab == editor_tab:
                tab_item.update_display()
                break

    def on_save_clicked(self, editor_tab):
        """Handle save button click"""
        parent = self.parent()
        while parent:
            if parent.__class__.__name__ == 'TextEditorWindow':
                parent.save_single_tab(editor_tab)
                break
            parent = parent.parent()

    def on_pin_clicked(self, editor_tab):
        """Handle pin button click"""
        parent = self.parent()
        while parent:
            if parent.__class__.__name__ == 'TextEditorWindow':
                parent.toggle_pin(editor_tab)
                break
            parent = parent.parent()

    def on_close_clicked(self, editor_tab):
        """Handle close button click"""
        parent = self.parent()
        while parent:
            if parent.__class__.__name__ == 'TextEditorWindow':
                parent.close_tab(editor_tab)
                break
            parent = parent.parent()

    def dragEnterEvent(self, event):
        """Handle drag enter event"""
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        """Handle drag leave event"""
        self.hide_drop_indicator()

    def hide_drop_indicator(self):
        """Hide the drop indicator"""
        # Use isHidden() check instead of isVisible() since isVisible() returns False
        # when widget or parents aren't shown, even if the widget itself is not hidden
        if not self.drop_indicator.isHidden():
            self.tab_layout.removeWidget(self.drop_indicator)
            self.drop_indicator.setVisible(False)
            self.drop_indicator_index = -1

    def show_drop_indicator_at(self, index):
        """Show drop indicator at specified index"""
        if self.drop_indicator_index != index:
            # Remove from old position
            if not self.drop_indicator.isHidden():
                self.tab_layout.removeWidget(self.drop_indicator)

            # Clamp index to valid range
            # The layout has tab items, potentially a divider, and a stretch at the end
            # Insert before the stretch (which is always at the last position)
            max_index = self.tab_layout.count() - 1
            index = max(0, min(index, max_index))

            # Insert at new position
            self.drop_indicator_index = index
            self.tab_layout.insertWidget(index, self.drop_indicator)
            self.drop_indicator.setVisible(True)

    def dragMoveEvent(self, event):
        """Handle drag move event"""
        try:
            # Ensure geometry is initialized before first drag
            self._ensure_geometry_initialized()

            if not event.mimeData().hasText():
                return

            # Get source index
            source_index = int(event.mimeData().text())
            if source_index < 0 or source_index >= len(self.tab_items):
                return

            # Get mouse position in widget coordinates
            if hasattr(event, 'position'):
                mouse_y = event.position().y()
            else:
                mouse_y = event.pos().y()

            # Find where we would drop based on mouse position
            # We'll insert BEFORE the first tab whose top edge is below the mouse
            target_index = len(self.tab_items)  # Default to end

            for i, tab_item in enumerate(self.tab_items):
                # Skip if tab doesn't have valid geometry yet
                if not tab_item.isVisible() or tab_item.height() == 0:
                    continue

                # Get the tab's position relative to this widget
                # Use mapToGlobal and mapFromGlobal for reliable coordinate conversion
                tab_global_pos = tab_item.mapToGlobal(tab_item.rect().topLeft())
                tab_local_pos = self.mapFromGlobal(tab_global_pos)
                tab_top = tab_local_pos.y()

                # If mouse is in the top half of this tab, insert before it
                tab_middle = tab_top + tab_item.height() / 2
                if mouse_y < tab_middle:
                    target_index = i
                    break

            # Check pinned status constraints
            source_item = self.tab_items[source_index]
            is_source_pinned = source_item.editor_tab.is_pinned
            pinned_count = sum(1 for item in self.tab_items if item.editor_tab.is_pinned)

            # Enforce constraint: pinned tabs can only be reordered within pinned section
            if is_source_pinned:
                # Pinned tabs: clamp to pinned section (0 to pinned_count)
                target_index = max(0, min(target_index, pinned_count))
            else:
                # Unpinned tabs: clamp to unpinned section (pinned_count to end)
                target_index = max(pinned_count, min(target_index, len(self.tab_items)))

            # Calculate layout index for drop indicator
            # This is where the indicator should appear in the layout
            layout_index = self._get_layout_index_for_tab_index(target_index, source_index)

            # Check if this would result in no movement (same position)
            # Apply the same adjustment logic as in dropEvent
            final_target_index = target_index
            if target_index > source_index:
                final_target_index = target_index - 1

            is_same_position = (source_index == final_target_index)

            # Update drop indicator color based on whether position would change
            if is_same_position:
                # Grey for no movement
                self.drop_indicator.setStyleSheet("background-color: #9E9E9E; min-height: 3px; max-height: 3px;")
            else:
                # Blue for movement
                self.drop_indicator.setStyleSheet("background-color: #2196F3; min-height: 3px; max-height: 3px;")

            self.show_drop_indicator_at(layout_index)
            event.acceptProposedAction()
        except Exception as e:
            # Silently handle errors to prevent crashes during drag
            print(f"Error in dragMoveEvent: {e}")
            self.hide_drop_indicator()

    def _get_layout_index_for_tab_index(self, tab_index, source_index=None):
        """
        Convert a tab_items index to a layout index, accounting for divider.
        tab_index: where we want to insert in tab_items (after removing source)
        source_index: the current position of the dragged tab (or None if not dragging)
        Returns: the layout index where the drop indicator should be shown
        """
        pinned_count = sum(1 for item in self.tab_items if item.editor_tab.is_pinned)
        has_divider = pinned_count > 0 and pinned_count < len(self.tab_items)

        # Start with the tab index
        layout_idx = tab_index

        # If there's a divider and we're at or past the unpinned section, add 1 for the divider
        if has_divider and tab_index >= pinned_count:
            layout_idx += 1

        return layout_idx

    def dropEvent(self, event):
        """Handle drop event to reorder tabs"""
        try:
            # Ensure geometry is initialized (should already be done by dragMoveEvent)
            self._ensure_geometry_initialized()

            # Hide the drop indicator
            self.hide_drop_indicator()

            if not event.mimeData().hasText():
                return

            # Get the source index
            source_index = int(event.mimeData().text())
            if source_index < 0 or source_index >= len(self.tab_items):
                return

            # Get mouse position in widget coordinates (same as dragMoveEvent)
            if hasattr(event, 'position'):
                mouse_y = event.position().y()
            else:
                mouse_y = event.pos().y()

            # Find where we would drop based on mouse position
            target_index = len(self.tab_items)  # Default to end

            for i, tab_item in enumerate(self.tab_items):
                # Skip if tab doesn't have valid geometry yet
                if not tab_item.isVisible() or tab_item.height() == 0:
                    continue

                # Get the tab's position relative to this widget
                # Use mapToGlobal and mapFromGlobal for reliable coordinate conversion
                tab_global_pos = tab_item.mapToGlobal(tab_item.rect().topLeft())
                tab_local_pos = self.mapFromGlobal(tab_global_pos)
                tab_top = tab_local_pos.y()

                # If mouse is in the top half of this tab, insert before it
                tab_middle = tab_top + tab_item.height() / 2
                if mouse_y < tab_middle:
                    target_index = i
                    break

            # Check pinned status constraints
            source_item = self.tab_items[source_index]
            is_source_pinned = source_item.editor_tab.is_pinned
            pinned_count = sum(1 for item in self.tab_items if item.editor_tab.is_pinned)

            # Enforce constraint: pinned tabs can only be reordered within pinned section
            if is_source_pinned:
                # Pinned tabs: clamp to pinned section (0 to pinned_count)
                target_index = max(0, min(target_index, pinned_count))
            else:
                # Unpinned tabs: clamp to unpinned section (pinned_count to end)
                target_index = max(pinned_count, min(target_index, len(self.tab_items)))

            # Adjust for the fact that source will be removed before insertion
            if target_index > source_index:
                target_index -= 1

            # Don't do anything if dropping on itself
            if source_index == target_index:
                event.acceptProposedAction()
                return

            # Reorder the tabs
            item = self.tab_items.pop(source_index)
            self.tab_items.insert(target_index, item)

            # Rebuild the layout
            for i in reversed(range(self.tab_layout.count())):
                layout_item = self.tab_layout.itemAt(i)
                if layout_item.widget():
                    self.tab_layout.removeItem(layout_item)

            for tab_item in self.tab_items:
                self.tab_layout.insertWidget(self.tab_layout.count() - 1, tab_item)

            self.update_pinned_divider()
            event.acceptProposedAction()
        except Exception as e:
            # Handle errors gracefully to prevent crashes
            print(f"Error in dropEvent: {e}")
            # Try to restore a consistent state
            self.hide_drop_indicator()
            event.acceptProposedAction()


