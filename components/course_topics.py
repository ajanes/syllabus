from flask_meld import Component

class CourseTopics(Component):
    """Component for selecting a course and displaying its topics."""

    selected_course = ""
    topics = []
    courses = []

    def mount(self, courses, course_topics):
        self.courses = courses
        self._course_topics = course_topics

    def updated_selected_course(self, new_id):
        self.topics = self._course_topics.get(new_id, [])
