from typing import List, Optional
from vrski.ui.element import UIElement

def find_elements(
    elements: List[UIElement],
    text: Optional[str] = None,
    element_id: Optional[str] = None,
    content_desc: Optional[str] = None,
    clickable: Optional[bool] = None,
    scrollable: Optional[bool] = None,
    editable: Optional[bool] = None,
    exact: bool = False
) -> List[UIElement]:
    """
    Filters a list of UIElements by various criteria.
    
    Args:
        elements: The list of UIElements to search in.
        text: Substring or exact match for element text.
        element_id: Substring or exact match for element resource-id.
        content_desc: Substring or exact match for content description.
        clickable: Filter by clickable status.
        scrollable: Filter by scrollable status.
        editable: Filter by editable status.
        exact: If True, performs exact case-sensitive matches on strings.
               If False (default), performs case-insensitive substring matches.
               
    Returns:
        A list of matching UIElements.
    """
    matched = []
    for el in elements:
        # Filter by text
        if text is not None:
            el_text = el.text or ""
            if exact:
                if el_text != text:
                    continue
            else:
                if text.lower() not in el_text.lower():
                    continue

        # Filter by resource-id (element_id)
        if element_id is not None:
            el_id = el.element_id or ""
            if exact:
                if el_id != element_id:
                    continue
            else:
                if element_id.lower() not in el_id.lower():
                    continue

        # Filter by content description
        if content_desc is not None:
            el_desc = el.content_desc or ""
            if exact:
                if el_desc != content_desc:
                    continue
            else:
                if content_desc.lower() not in el_desc.lower():
                    continue

        # Filter by clickable
        if clickable is not None and el.clickable != clickable:
            continue

        # Filter by scrollable
        if scrollable is not None and el.scrollable != scrollable:
            continue

        # Filter by editable
        if editable is not None and el.editable != editable:
            continue

        matched.append(el)
    return matched

def find_first(
    elements: List[UIElement],
    text: Optional[str] = None,
    element_id: Optional[str] = None,
    content_desc: Optional[str] = None,
    clickable: Optional[bool] = None,
    scrollable: Optional[bool] = None,
    editable: Optional[bool] = None,
    exact: bool = False
) -> Optional[UIElement]:
    """
    Finds the first UIElement matching the criteria, or None.
    """
    results = find_elements(
        elements=elements,
        text=text,
        element_id=element_id,
        content_desc=content_desc,
        clickable=clickable,
        scrollable=scrollable,
        editable=editable,
        exact=exact
    )
    return results[0] if results else None
