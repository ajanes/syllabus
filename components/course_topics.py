from flask_meld import Component

class CourseTopics(Component):
    """Component for selecting a course and displaying its topics."""

    selected_year = ""
    selected_semester = ""
    selected_course = ""
    topics = []
    courses = []
    years = []

    def mount(self, courses, course_topics, years):
        self._all_courses = courses
        self.years = years
        self._course_topics = course_topics
        self.filter_courses()

    def updated_selected_year(self, _):
        self.selected_course = ""
        self.filter_courses()

    def updated_selected_semester(self, _):
        self.selected_course = ""
        self.filter_courses()

    def updated_selected_course(self, new_id):
        self.topics = self._course_topics.get(new_id, [])

    def filter_courses(self):
        self.courses = [
            c
            for c in self._all_courses
            if (not self.selected_year or c["year"] == self.selected_year)
            and (not self.selected_semester or c["semester"] == self.selected_semester)
        ]
        if not any(c["id"] == self.selected_course for c in self.courses):
            self.selected_course = ""
            self.topics = []
