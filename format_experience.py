def format_experience(experience_list):
    if not isinstance(experience_list, list):
        return "N/A"

    formatted_experience = []
    for item in experience_list:
        details = []
        for key, value in item.items():
            if value:  # Include only non-empty values
                # Format the key-value pair in key: value format
                details.append(f"{key}: {value}")
        # Join details with a newline and ensure proper indentation for each item
        formatted_experience.append("\n".join(details))
    # Separate each experience entry with an additional newline for clarity
    return "\n\n".join(formatted_experience)


# Example usage
experience_list = [
    {
        "organisation_name": "Al Rabie Saudi Foods Co Ltd",
        "duration": "2 years 4 months (August 2022 - Present)",
        "profile": "Quality Control Specialist",
    }
]

formatted_output = format_experience(experience_list)
print(formatted_output)
